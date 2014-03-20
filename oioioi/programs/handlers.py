from django.db import transaction
from django.core.urlresolvers import reverse
from django.utils.translation import ugettext_lazy as _
from oioioi.base.utils import get_object_by_dotted_name, make_html_link
from oioioi.sioworkers.jobs import run_sioworkers_job, run_sioworkers_jobs
from oioioi.contests.scores import ScoreValue
from oioioi.contests.models import Submission, SubmissionReport, \
        ScoreReport
from oioioi.programs.models import CompilationReport, TestReport, \
        GroupReport, Test, UserOutGenStatus
from oioioi.programs.utils import slice_str
from oioioi.problems.models import Problem
from oioioi.filetracker.client import get_client
from oioioi.filetracker.utils import django_to_filetracker_path, \
        filetracker_to_django_file

import logging
import functools
from collections import defaultdict
import types

logger = logging.getLogger(__name__)

DEFAULT_TEST_SCORER = \
        'oioioi.programs.utils.discrete_test_scorer'
DEFAULT_GROUP_SCORER = \
        'oioioi.programs.utils.min_group_scorer'
DEFAULT_SCORE_AGGREGATOR = \
        'oioioi.programs.utils.sum_score_aggregator'


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


def _if_compiled(fn):
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
    """

    compilation_job = env.copy()
    compilation_job['job_type'] = 'compile'
    compilation_job['out_file'] = _make_filename(env, 'exe')
    if 'language' in env and 'compiler' not in env:
        compilation_job['compiler'] = 'default-' + env['language']

    new_env = run_sioworkers_job(compilation_job)

    env['compiled_file'] = new_env.get('out_file')
    env['compilation_message'] = new_env.get('compiler_output', '')
    env['compilation_result'] = new_env.get('result_code', 'CE')
    return env


@_if_compiled
@transaction.commit_on_success
def collect_tests(env, **kwargs):
    """Collects tests from the database and converts them to
       evaluation environments.

       Used ``environ`` keys:
         * ``problem_id``

       Produced ``environ`` keys:
          * ``tests``: a dictionary mapping test names to test envs
    """

    env.setdefault('tests', {})

    if 'tests_subset' in env['extra_args']:
        tests = Test.objects.in_bulk(env['extra_args']['tests_subset']) \
                                                                    .values()
    else:
        problem = Problem.objects.get(id=env['problem_id'])
        tests = Test.objects.filter(problem=problem)

    for test in tests:
        test_env = {}
        test_env['id'] = test.id
        test_env['name'] = test.name
        test_env['in_file'] = django_to_filetracker_path(test.input_file)
        test_env['hint_file'] = django_to_filetracker_path(test.output_file)
        test_env['kind'] = test.kind
        test_env['group'] = test.group or test.name
        test_env['max_score'] = test.max_score
        if test.time_limit:
            test_env['exec_time_limit'] = test.time_limit
        if test.memory_limit:
            test_env['exec_mem_limit'] = test.memory_limit
        env['tests'][test.name] = test_env

    return env


@_if_compiled
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
    for test_name, test_env in env['tests'].iteritems():
        if kind and test_env['kind'] != kind:
            continue
        job = test_env.copy()
        job['job_type'] = (env.get('exec_mode', '') + '-exec').lstrip('-')
        job['exe_file'] = env['compiled_file']
        job['check_output'] = env.get('check_outputs', True)
        if env.get('checker'):
            job['chk_file'] = env['checker']
        if env.get('save_outputs'):
            job.setdefault('out_file', _make_filename(env, test_name + '.out'))
            job['upload_out'] = True
        jobs[test_name] = job

    extra_args = env.get('sioworkers_extra_args', {}).get(kind, {})
    jobs = run_sioworkers_jobs(jobs, **extra_args)
    env.setdefault('test_results', {})
    for test_name, result in jobs.iteritems():
        env['test_results'].setdefault(test_name, {}).update(result)
    return env


@_if_compiled
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

    fun = get_object_by_dotted_name(env.get('test_scorer')
            or DEFAULT_TEST_SCORER)
    tests = env['tests']

    for test_name, test_result in env['test_results'].iteritems():
        score, max_score, status = fun(tests[test_name], test_result)
        assert isinstance(score, (types.NoneType, ScoreValue))
        assert isinstance(max_score, (types.NoneType, ScoreValue))
        test_result['score'] = score and score.serialize()
        test_result['max_score'] = max_score and max_score.serialize()
        test_result['status'] = status
    return env


@_if_compiled
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
    for test_name, test in env['test_results'].iteritems():
        group_name = env['tests'][test_name]['group']
        test_results[group_name][test_name] = test

    env.setdefault('group_results', {})
    for group_name, results in test_results.iteritems():
        if group_name in env['group_results']:
            continue
        fun = get_object_by_dotted_name(env.get('group_scorer',
                    DEFAULT_GROUP_SCORER))
        score, max_score, status = fun(results)
        if not isinstance(score, (types.NoneType, ScoreValue)):
            raise TypeError("Group scorer returned %r as score, "
                    "not None or ScoreValue" % (type(score),))
        if not isinstance(max_score, (types.NoneType, ScoreValue)):
            raise TypeError("Group scorer returned %r as max_score, "
                    "not None or ScoreValue" % (type(max_score),))
        group_result = {}
        group_result['score'] = score and score.serialize()
        group_result['max_score'] = max_score and max_score.serialize()
        group_result['status'] = status
        one_of_tests = env['tests'][results.iterkeys().next()]
        if not all(env['tests'][key]['kind'] == one_of_tests['kind']
                for key in results.iterkeys()):
            raise ValueError("Tests in group '%s' have different kinds. "
                "This is not supported." % (group_name,))
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

    fun = get_object_by_dotted_name(env.get('score_aggregator')
            or DEFAULT_SCORE_AGGREGATOR)

    if kind is None:
        group_results = env['group_results']
    else:
        group_results = dict((name, res) for (name, res)
                             in env['group_results'].iteritems()
                             if res['kind'] == kind)

    score, max_score, status = fun(group_results)
    assert isinstance(score, (types.NoneType, ScoreValue))
    assert isinstance(max_score, (types.NoneType, ScoreValue))
    env['score'] = score and score.serialize()
    env['max_score'] = max_score and max_score.serialize()
    env['status'] = status

    return env


def _make_base_report(env, kind):
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
    submission = Submission.objects.get(id=env['submission_id'])
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

    if not isinstance(compilation_message, unicode):
        compilation_message = compilation_message.decode('utf8')
    compilation_report.compiler_output = compilation_message
    compilation_report.save()

    return submission, submission_report


@transaction.commit_on_success
def make_report(env, kind='NORMAL', scores=True, **kwargs):
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
    for test_name, result in test_results.iteritems():
        test = tests[test_name]
        if 'report_id' in result:
            continue
        test_report = TestReport(submission_report=submission_report)
        test_report.test_id = test.get('id')
        test_report.test_name = test_name
        test_report.test_group = test['group']
        test_report.test_time_limit = test.get('exec_time_limit')
        test_report.test_max_score = test['max_score']
        test_report.score = scores and result['score'] or None
        test_report.status = result['status']
        test_report.time_used = result['time_used']
        comment = result.get('result_string', '')
        if comment.lower() == 'ok':  # Annoying
            comment = ''
        test_report.comment = slice_str(comment, TestReport.
                _meta.get_field('comment').max_length)
        if env.get('save_outputs', False):
            test_report.output_file = filetracker_to_django_file(
                                                            result['out_file'])
        test_report.save()
        result['report_id'] = test_report.id

    group_results = env.get('group_results', {})
    for group_name, group_result in group_results.iteritems():
        if 'report_id' in group_result:
            continue
        group_report = GroupReport(submission_report=submission_report)
        group_report.group = group_name
        group_report.score = scores and group_result['score'] or None
        group_report.max_score = scores and group_result['max_score'] or None
        group_report.status = group_result['status']
        group_report.save()
        group_result['result_id'] = group_report.id

    if kind == 'INITIAL':
        if submission.user is not None and not env.get('is_rejudge', False):
            logger.info("Submission %(submission_id)d by user %(username)s"
                        " for problem %(short_name)s got initial result.",
                        {'submission_id': submission.pk,
                         'username': submission.user.username,
                         'short_name': submission.problem_instance
                                    .short_name},
                            extra={'notification': 'initial_results',
                                   'user': submission.user,
                                   'submission': submission})

    return env


def delete_executable(env, **kwargs):
    if 'compiled_file' in env:
        get_client().delete_file(env['compiled_file'])
    return env


def fill_outfile_in_existing_test_reports(env, **kwargs):
    """Fill output files into existing test reports that are not directly
       related to present submission. Also change status of UserOutGenStatus
       object to finished.

       Used ``environ`` keys:
           * ``extra_args`` dictionary with ``submission_report`` object
           * ``test_results``
    """
    if 'submission_report' not in env['extra_args']:
        logger.info('No submission_report given to fill tests outputs')
        return env

    submission_report = env['extra_args']['submission_report']
    test_reports = TestReport.objects.filter(
                                        submission_report=submission_report)
    test_results = env.get('test_results', {})

    for test_name, result in test_results.iteritems():
        try:
            testreport = test_reports.get(test_name=test_name)
        except (TestReport.DoesNotExist, TestReport.MultipleObjectsReturned):
            logger.warn('Test report for test: %s can not be determined',
                           test_name)
            continue

        if bool(testreport.output_file):
            logger.warn('Output for test report %s exists. Deleting old one.'
                        % (testreport.id))
            get_client().delete_file(testreport.output_file)

        testreport.output_file = filetracker_to_django_file(result['out_file'])
        testreport.save()

        try:
            download_controller = UserOutGenStatus.objects.get(
                                                        testreport=testreport)
        except UserOutGenStatus.DoesNotExist:
            download_controller = UserOutGenStatus(testreport=testreport)

        download_controller.status = 'OK'
        download_controller.save()

    return env


def insert_existing_submission_link(env, **kwargs):
    """Add comment to some existing submission with link to submission view
       of present submission.

       Used ``environ`` keys:
           * ``extra_args`` dictionary with ``submission_report`` object
           * ``contest_id``
           * ``submission_id``
    """
    if 'submission_report' not in env['extra_args']:
        logger.info('No submission_report given to generate link')
        return env

    submission_report = env['extra_args']['submission_report']
    dst_submission = submission_report.submission
    src_submission = Submission.objects.get(id=env['submission_id'])
    href = reverse('submission', kwargs={'submission_id': dst_submission.id,
                                         'contest_id': env['contest_id']})
    html_link = make_html_link(href, _("submission report") + ": " +
                               str(dst_submission.id))
    test_names = ', '.join(env.get('test_results', {}).keys())
    src_submission.comment = \
        "This is an internal submission created after someone requested to " \
        "generate user output(s) on test(s): " + test_names + \
        ", related to " + html_link
    src_submission.save()

    return env
