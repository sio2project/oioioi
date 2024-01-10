import functools
import logging
from collections import defaultdict

from django.conf import settings
from django.db import transaction
from django.urls import reverse
from django.utils.module_loading import import_string
from django.utils.text import Truncator
from django.utils.translation import gettext_lazy as _

from oioioi.base.utils import make_html_link
from oioioi.contests.handlers import _get_submission_or_skip
from oioioi.contests.models import ScoreReport, SubmissionReport
from oioioi.contests.scores import IntegerScore, ScoreValue
from oioioi.evalmgr.tasks import transfer_job
from oioioi.filetracker.client import get_client
from oioioi.filetracker.utils import (
    django_to_filetracker_path,
    filetracker_to_django_file,
)
from oioioi.programs.models import (
    CompilationReport,
    GroupReport,
    Test,
    TestReport,
    UserOutGenStatus,
    LanguageOverrideForTest,
)

logger = logging.getLogger(__name__)

COMPILE_TASK_PRIORITY = 200
EXAMPLE_TEST_TASK_PRIORITY = 300
TESTRUN_TEST_TASK_PRIORITY = 300
DEFAULT_TEST_TASK_PRIORITY = 100
# There is also TASK_PRIORITY in oioioi/sinolpack/package.py.


def _make_filename(env, base_name):
    """Create a filename in the filetracker for storing outputs
    from filetracker jobs.

    By default the path is of the form
    ``/eval/<contest_id>/<submission_id>/<job_id>-<base_name>``
    with fields absent from ``env`` skipped. The folder can be also
    specified in ``env['eval_dir']``.
    """
    if 'eval_dir' not in env:
        eval_dir = '/eval'
        if 'contest_id' in env:
            eval_dir += '/%s' % env['contest_id']
        if 'submission_id' in env:
            eval_dir += '/%s' % env['submission_id']
        env['eval_dir'] = eval_dir
    return '%s/%s-%s' % (env['eval_dir'], env['job_id'], base_name)


def _skip_on_compilation_error(fn):
    """A decorator which skips the decorated function if the
    compilation fails.

    This is checked by looking for ``OK`` in ``env['compilation_result']``.
    If the key is not present, it is assumed that the compilation succeeded.
    """

    @functools.wraps(fn)
    def decorated(env, **kwargs):
        if env.get('compilation_result', 'OK') != 'OK':
            return env
        return fn(env, **kwargs)

    return decorated


def compile(env, **kwargs):
    """Compiles source file on the remote machine and returns name of
    the executable that may be ran

    USES
       * env['source_file'] - source file name
       * env['language'] - if ``env['compiler']`` is not set and
         ``env['language']`` is, the compiler is set to ``'default-' +
         env['language']``.
       * the entire ``env`` is also passed to the ``compile`` job

    PRODUCES
       * env['compilation_result'] - may be OK if the file compiled
         successfully or CE otherwise.
       * env['compiled_file'] - exists if and only if
         env['compilation_result'] is set to OK and contains compiled
         binary path
       * env['compilation_message'] - contains compiler stdout and stderr
       * env['exec_info'] - information how to execute the compiled file
    """

    compilation_job = env.copy()
    compilation_job['job_type'] = 'compile'
    compilation_job['task_priority'] = COMPILE_TASK_PRIORITY
    compilation_job['out_file'] = _make_filename(env, 'exe')
    if 'language' in env and 'compiler' not in env:
        compilation_job['compiler'] = 'default-' + env['language']
    env['workers_jobs'] = {'compile': compilation_job}
    return transfer_job(
        env,
        'oioioi.sioworkers.handlers.transfer_job',
        'oioioi.sioworkers.handlers.restore_job',
    )


def compile_end(env, **kwargs):
    new_env = env['workers_jobs.results']['compile']
    env['compiled_file'] = new_env.get('out_file')
    env['compilation_message'] = new_env.get('compiler_output', '')
    env['compilation_result'] = new_env.get('result_code', 'CE')
    env['exec_info'] = new_env.get('exec_info', {})
    return env


def _override_tests_limits(language, tests):
    """ Given language and list of Test objects, returns
    the dictionary of memory and time limits.
    The key is test's pk.
    In case language overriding is defined in the database,
    the value of key is specified by overriding. Otherwise,
    the limits are the same as initial.
    """

    overriding_tests = LanguageOverrideForTest.objects.filter(
        test__in=tests, language=language
    )
    new_limits = {}

    for test in tests:
        new_limits[test.pk] = {
            'memory_limit': test.memory_limit,
            'time_limit': test.time_limit,
        }

    for new_rule in overriding_tests:
        new_limits[new_rule.test.pk]['memory_limit'] = new_rule.memory_limit
        new_limits[new_rule.test.pk]['time_limit'] = new_rule.time_limit

    return new_limits


@_skip_on_compilation_error
@transaction.atomic
def collect_tests(env, **kwargs):
    """Collects tests from the database and converts them to
    evaluation environments.

    Used ``environ`` keys:
      * ``problem_instance_id``
      * ``language``
      * ``extra_args``
      * ``is_rejudge``

    Produced ``environ`` keys:
       * ``tests``: a dictionary mapping test names to test envs
    """
    env.setdefault('tests', {})

    if 'tests_subset' in env['extra_args']:
        tests = list(Test.objects.in_bulk(env['extra_args']['tests_subset']).values())
    else:
        tests = Test.objects.filter(
            problem_instance__id=env['problem_instance_id'], is_active=True
        )

    problem_instance = env['problem_instance_id']
    if env['is_rejudge']:
        submission = env['submission_id']
        rejudge_type = env['extra_args'].setdefault('rejudge_type', 'FULL')
        tests_to_judge = env['extra_args'].setdefault('tests_to_judge', [])
        test_reports = TestReport.objects.filter(
            submission_report__submission__id=submission,
            submission_report__status='ACTIVE',
        )
        tests_used = [report.test_name for report in test_reports]
        if rejudge_type == 'NEW':
            tests_to_judge = [
                t.name
                for t in Test.objects.filter(
                    problem_instance__id=problem_instance, is_active=True
                ).exclude(name__in=tests_used)
            ]
        elif rejudge_type == 'JUDGED':
            tests = Test.objects.filter(
                problem_instance__id=problem_instance, name__in=tests_used
            )
            tests_to_judge = [t for t in tests_to_judge if t in tests_used]
        elif rejudge_type == 'FULL':
            tests_to_judge = [t.name for t in tests]
    else:
        tests_to_judge = [t.name for t in tests]

    # Some of the tests may be overriden, e.g. adding additional
    # overhead in time limits for Python submissions.
    language = env['language']
    new_limits = _override_tests_limits(language, tests)

    for test in tests:
        test_env = {}
        test_env['id'] = test.id
        test_env['name'] = test.name
        test_env['in_file'] = django_to_filetracker_path(test.input_file)
        test_env['hint_file'] = django_to_filetracker_path(test.output_file)
        test_env['kind'] = test.kind
        test_env['group'] = test.group or test.name
        test_env['max_score'] = test.max_score
        test_env['order'] = test.order
        if test.time_limit:
            test_env['exec_time_limit'] = new_limits[test.pk]['time_limit']
        if test.memory_limit:
            test_env['exec_mem_limit'] = new_limits[test.pk]['memory_limit']
        test_env['to_judge'] = False
        env['tests'][test.name] = test_env

    for test in tests_to_judge:
        env['tests'][test]['to_judge'] = True
    return env


@_skip_on_compilation_error
def run_tests(env, kind=None, **kwargs):
    """Runs tests and saves their results into the environment

    If ``kind`` is specified, only tests with the given kind will be run.

    Used ``environ`` keys:
      * ``tests``: this should be a dictionary, mapping test name into
        the environment to pass to the ``exec`` job
      * ``unsafe_exec``: set to ``True`` if we want to use only
        ``ulimit()`` to limit the executable file resources, ``False``
        otherwise (see the documentation for ``unsafe-exec`` job for
        more information),
      * ``compiled_file``: the compiled file which will be tested,
      * ``exec_info``: information how to execute ``compiled_file``
      * ``check_outputs``: set to ``True`` if the output should be verified
      * ``checker``: if present, it should be the filetracker path
        of the binary used as the output checker,
      * ``save_outputs``: set to ``True`` if and only if each of
        test results should have its output file attached.
      * ``sioworkers_extra_args``: dict mappting kinds to additional
        arguments passed to
        :fun:`oioioi.sioworkers.jobs.run_sioworkers_jobs`
        (kwargs).

    Produced ``environ`` keys:
      * ``test_results``: a dictionary, mapping test names into
        dictionaries with the following keys:

          ``result_code``
            test status: OK, WA, RE, ...
          ``result_string``
            detailed supervisor information (for example, where the
            required and returned outputs differ)
          ``time_used``
            total time used, in miliseconds
          ``mem_used``
            memory usage, in KiB
          ``num_syscalls``
            number of syscalls performed
          ``out_file``
            filetracker path to the output file (only if
            ``env['save_outputs']`` was set)

        If the dictionary already exists, new test results are appended.
    """
    jobs = dict()
    not_to_judge = []
    for test_name, test_env in env['tests'].items():
        if kind and test_env['kind'] != kind:
            continue
        if not test_env['to_judge']:
            not_to_judge.append(test_name)
            continue
        job = test_env.copy()
        job['job_type'] = (env.get('exec_mode', '') + '-exec').lstrip('-')
        if kind == 'INITIAL' or kind == 'EXAMPLE':
            job['task_priority'] = EXAMPLE_TEST_TASK_PRIORITY
        elif env['submission_kind'] == 'TESTRUN':
            job['task_priority'] = TESTRUN_TEST_TASK_PRIORITY
        else:
            job['task_priority'] = DEFAULT_TEST_TASK_PRIORITY
        job['exe_file'] = env['compiled_file']
        job['exec_info'] = env['exec_info']
        job['check_output'] = env.get('check_outputs', True)
        if env.get('checker'):
            job['chk_file'] = env['checker']
        if env.get('save_outputs'):
            job.setdefault('out_file', _make_filename(env, test_name + '.out'))
            job['upload_out'] = True
        job['untrusted_checker'] = env['untrusted_checker']
        jobs[test_name] = job
    extra_args = env.get('sioworkers_extra_args', {}).get(kind, {})
    env['workers_jobs'] = jobs
    env['workers_jobs.extra_args'] = extra_args
    env['workers_jobs.not_to_judge'] = not_to_judge
    return transfer_job(
        env,
        'oioioi.sioworkers.handlers.transfer_job',
        'oioioi.sioworkers.handlers.restore_job',
    )


@_skip_on_compilation_error
def run_tests_end(env, **kwargs):
    not_to_judge = env['workers_jobs.not_to_judge']
    del env['workers_jobs.not_to_judge']
    jobs = env['workers_jobs.results']
    env.setdefault('test_results', {})
    for test_name, result in jobs.items():
        env['test_results'].setdefault(test_name, {}).update(result)
    for test_name in not_to_judge:
        env['test_results'].setdefault(test_name, {}).update(env['tests'][test_name])
    return env


@_skip_on_compilation_error
def grade_tests(env, **kwargs):
    """Grades tests using a scoring function.

    The ``env['test_scorer']``, which is used by this ``Handler``,
    should be a path to a function which gets test definition (e.g.  a
    ``env['tests'][test_name]`` dict) and test run result (e.g.  a
    ``env['test_results'][test_name]`` dict) and returns a score
    (instance of some subclass of
    :class:`~oioioi.contests.scores.ScoreValue`) and a status.

    Used ``environ`` keys:
      * ``tests``
      * ``test_results``
      * ``test_scorer``

    Produced ``environ`` keys:
      * `score`, `max_score` and `status` keys in ``env['test_result']``
    """

    fun = import_string(env.get('test_scorer') or settings.DEFAULT_TEST_SCORER)
    tests = env['tests']
    for test_name, test_result in env['test_results'].items():
        if tests[test_name]['to_judge']:
            score, max_score, status = fun(tests[test_name], test_result)
            assert isinstance(score, (type(None), ScoreValue))
            assert isinstance(max_score, (type(None), ScoreValue))
            test_result['score'] = score and score.serialize()
            test_result['max_score'] = max_score and max_score.serialize()
            test_result['status'] = status
        else:
            report = TestReport.objects.get(
                submission_report__submission__id=env['submission_id'],
                submission_report__status='ACTIVE',
                test_name=test_name,
            )
            score = report.score
            max_score = report.max_score
            status = report.status
            time_used = report.time_used
            test_result['score'] = score and score.serialize()
            test_result['max_score'] = max_score and max_score.serialize()
            test_result['status'] = status
            test_result['time_used'] = time_used
            env['test_results'][test_name] = test_result
    return env


@_skip_on_compilation_error
def grade_groups(env, **kwargs):
    """Grades ungraded groups using a aggregating function.

    The ``group_scorer`` key in ``env`` should contain the path to
    a function which gets a list of test results (wihtout their names) and
    returns an aggregated score (instance of some subclass of
    :class:`~oioioi.contests.scores.ScoreValue`).

    Used ``environ`` keys:
      * ``tests``
      * ``test_results``
      * ``group_scorer``

    Produced ``environ`` keys:
      * `score`, `max_score` and `status` keys in ``env['group_results']``
    """

    test_results = defaultdict(dict)
    for test_name, test in env['test_results'].items():
        group_name = env['tests'][test_name]['group']
        test_results[group_name][test_name] = test

    env.setdefault('group_results', {})
    for group_name, results in test_results.items():
        if group_name in env['group_results']:
            continue
        fun = import_string(env.get('group_scorer', settings.DEFAULT_GROUP_SCORER))
        score, max_score, status = fun(results)
        if not isinstance(score, (type(None), ScoreValue)):
            raise TypeError(
                "Group scorer returned %r as score, "
                "not None or ScoreValue" % (type(score),)
            )
        if not isinstance(max_score, (type(None), ScoreValue)):
            raise TypeError(
                "Group scorer returned %r as max_score, "
                "not None or ScoreValue" % (type(max_score),)
            )
        group_result = {}
        group_result['score'] = score and score.serialize()
        group_result['max_score'] = max_score and max_score.serialize()
        group_result['status'] = status
        one_of_tests = env['tests'][next(iter(results.keys()))]
        if not all(
            env['tests'][key]['kind'] == one_of_tests['kind']
            for key in results.keys()
        ):
            raise ValueError(
                "Tests in group '%s' have different kinds. "
                "This is not supported." % (group_name,)
            )
        group_result['kind'] = one_of_tests['kind']
        env['group_results'][group_name] = group_result

    return env


def grade_submission(env, kind='NORMAL', **kwargs):
    """Grades submission with specified kind of tests on a `Job` layer.

    If ``kind`` is None, all tests will be graded.

    This `Handler` aggregates score from graded groups and gets
    submission status from tests results.

    Used ``environ`` keys:
        * ``group_results``
        * ``test_results``
        * ``score_aggregator``

    Produced ``environ`` keys:
        * ``status``
        * ``score``
        * ``max_score``
    """

    # TODO: let score_aggregator handle compilation errors

    if env.get('compilation_result', 'OK') != 'OK':
        env['score'] = None
        env['max_score'] = None
        env['status'] = 'CE'
        return env

    fun = import_string(
        env.get('score_aggregator') or settings.DEFAULT_SCORE_AGGREGATOR
    )

    if kind is None:
        group_results = env['group_results']
    else:
        group_results = dict(
            (name, res)
            for (name, res) in env['group_results'].items()
            if res['kind'] == kind
        )

    score, max_score, status = fun(group_results)
    assert isinstance(score, (type(None), ScoreValue))
    assert isinstance(max_score, (type(None), ScoreValue))
    env['score'] = score and score.serialize()
    env['max_score'] = max_score and max_score.serialize()
    env['status'] = status

    return env


@_get_submission_or_skip
def _make_base_report(env, submission, kind):
    """Helper function making: SubmissionReport, ScoreReport,
    CompilationReport.

    Used ``environ`` keys:
        * ``status``
        * ``score``
        * ``compilation_result``
        * ``compilation_message``
        * ``submission_id``
        * ``max_score``

    Alters ``environ`` by adding:
        * ``report_id``: id of the produced
          :class:`~oioioi.contests.models.SubmissionReport`

    Returns: tuple (submission, submission_report)
    """
    submission_report = SubmissionReport(submission=submission)
    submission_report.kind = kind
    submission_report.save()

    env['report_id'] = submission_report.id

    status_report = ScoreReport(submission_report=submission_report)
    status_report.status = env['status']
    status_report.score = env['score']
    status_report.max_score = env['max_score']
    status_report.save()

    compilation_report = CompilationReport(submission_report=submission_report)
    compilation_report.status = env['compilation_result']
    compilation_message = env['compilation_message']

    if not isinstance(compilation_message, str):
        compilation_message = compilation_message.decode('utf8')
    compilation_report.compiler_output = compilation_message
    compilation_report.save()

    return submission, submission_report


@transaction.atomic
def make_report(env, kind='NORMAL', save_scores=True, **kwargs):
    """Builds entities for tests results in a database.

    Used ``environ`` keys:
        * ``tests``
        * ``test_results``
        * ``group_results``
        * ``status``
        * ``score``
        * ``compilation_result``
        * ``compilation_message``
        * ``submission_id``

    Produced ``environ`` keys:
        * ``report_id``: id of the produced
          :class:`~oioioi.contests.models.SubmissionReport`
    """
    submission, submission_report = _make_base_report(env, kind)

    if env['compilation_result'] != 'OK':
        return env
    tests = env['tests']

    test_results = env.get('test_results', {})
    for test_name, result in test_results.items():
        test = tests[test_name]
        if 'report_id' in result:
            continue
        test_report = TestReport(submission_report=submission_report)
        test_report.test_id = test.get('id')
        test_report.test_name = test_name
        test_report.test_group = test['group']
        test_report.test_time_limit = result['exec_time_limit']
        test_report.max_score = result['max_score']
        test_report.score = result['score'] if save_scores else None
        test_report.status = result['status']
        test_report.time_used = result['time_used']

        comment = result.get('result_string', '')
        if comment.lower() in ['ok', 'time limit exceeded']:  # Annoying
            comment = ''
        max_comment_length = TestReport._meta.get_field('comment').max_length
        test_report.comment = (comment[:max_comment_length - 1] + '…') if len(comment) > max_comment_length else comment
        if env.get('save_outputs', False):
            test_report.output_file = filetracker_to_django_file(result['out_file'])
        test_report.save()
        result['report_id'] = test_report.id

    group_results = env.get('group_results', {})
    for group_name, group_result in group_results.items():
        if 'report_id' in group_result:
            continue
        group_report = GroupReport(submission_report=submission_report)
        group_report.group = group_name
        group_report.score = group_result['score'] if save_scores else None
        group_report.max_score = group_result['max_score'] if save_scores else None
        group_report.status = group_result['status']
        group_report.save()
        group_result['result_id'] = group_report.id

    if kind == 'INITIAL':
        if submission.user is not None and not env.get('is_rejudge', False):
            logger.info(
                "Submission %(submission_id)d by user %(username)s"
                " for problem %(short_name)s got initial result.",
                {
                    'submission_id': submission.pk,
                    'username': submission.user.username,
                    'short_name': submission.problem_instance.short_name,
                },
                extra={
                    'notification': 'initial_results',
                    'user': submission.user,
                    'submission': submission,
                },
            )

    return env


@_skip_on_compilation_error
def delete_executable(env, **kwargs):
    if 'compiled_file' in env:
        get_client().delete_file(env['compiled_file'])
    return env


@transaction.atomic
def fill_outfile_in_existing_test_reports(env, **kwargs):
    """Fill output files into existing test reports that are not directly
    related to present submission. Also change status of UserOutGenStatus
    object to finished.

    Used ``environ`` keys:
        * ``extra_args`` dictionary with ``submission_report`` object
        * ``test_results``
    """
    if 'submission_report_id' not in env['extra_args']:
        logger.info('No submission_report given to fill tests outputs')
        return env

    submission_report_id = env['extra_args']['submission_report_id']
    submission_report = SubmissionReport.objects.get(id=submission_report_id)
    test_reports = TestReport.objects.filter(submission_report=submission_report)
    test_results = env.get('test_results', {})

    for test_name, result in test_results.items():
        try:
            testreport = test_reports.get(test_name=test_name)
        except (TestReport.DoesNotExist, TestReport.MultipleObjectsReturned):
            logger.warning('Test report for test: %s can not be determined', test_name)
            continue

        if testreport.output_file:
            logger.warning(
                'Output for test report %s exists. Deleting old one.', testreport.id
            )
            get_client().delete_file(testreport.output_file)

        testreport.output_file = filetracker_to_django_file(result['out_file'])
        testreport.save()

        try:
            download_controller = UserOutGenStatus.objects.get(testreport=testreport)
        except UserOutGenStatus.DoesNotExist:
            download_controller = UserOutGenStatus(testreport=testreport)

        download_controller.status = 'OK'
        download_controller.save()

    return env


@transaction.atomic
@_get_submission_or_skip
def insert_existing_submission_link(env, src_submission, **kwargs):
    """Add comment to some existing submission with link to submission view
    of present submission.

    Used ``environ`` keys:
        * ``extra_args`` dictionary with ``submission_report`` object
        * ``contest_id``
        * ``submission_id``
    """
    if 'submission_report_id' not in env['extra_args']:
        logger.info('No submission_report given to generate link')
        return env

    submission_report_id = env['extra_args']['submission_report_id']
    submission_report = SubmissionReport.objects.get(id=submission_report_id)
    dst_submission = submission_report.submission
    href = reverse(
        'submission',
        kwargs={'submission_id': dst_submission.id, 'contest_id': env['contest_id']},
    )
    html_link = make_html_link(
        href, _("submission report") + ": " + str(dst_submission.id)
    )
    test_names = ', '.join(list(env.get('test_results', {}).keys()))

    # Note that the comment is overwritten by safe string.
    src_submission.comment = (
        "This is an internal submission created after someone requested to "
        "generate user output on tests: %s, related to %s" % (test_names, html_link)
    )
    src_submission.save()

    return env
