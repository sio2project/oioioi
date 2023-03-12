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
from oioioi.encdec.models import (
    LanguageOverrideForEncdecTest,
    EncdecTest,
    EncdecTestReport,
    EncdecUserOutGenStatus,
)
from oioioi.evalmgr.tasks import transfer_job
from oioioi.filetracker.client import get_client
from oioioi.filetracker.utils import (
    django_to_filetracker_path,
    filetracker_to_django_file,
)
from oioioi.programs.handlers import (
    COMPILE_TASK_PRIORITY,
    DEFAULT_TEST_TASK_PRIORITY,
    EXAMPLE_TEST_TASK_PRIORITY,
    TESTRUN_TEST_TASK_PRIORITY,
    _make_filename,
    _skip_on_compilation_error,
)
from oioioi.programs.models import (
    CompilationReport,
    GroupReport,
)

logger = logging.getLogger(__name__)


def _override_tests_limits(language, tests):
    """ Given language and list of EncdecTest objects, returns
    the dictionary of memory and time limits.
    The key is test's pk.
    In case language overriding is defined in the database,
    the value of key is specified by overriding. Otherwise,
    the limits are the same as initial.
    """

    overriding_tests = LanguageOverrideForEncdecTest.objects.filter(
        test__in=tests, language=language
    )
    new_limits = {}

    for test in tests:
        new_limits[test.pk] = {
            'encoder_memory_limit': test.encoder_memory_limit,
            'decoder_memory_limit': test.decoder_memory_limit,
            'encoder_time_limit': test.encoder_time_limit,
            'decoder_time_limit': test.decoder_time_limit,
        }

    for new_rule in overriding_tests:
        new_limits[new_rule.test.pk]['encoder_memory_limit'] = new_rule.encoder_memory_limit
        new_limits[new_rule.test.pk]['decoder_memory_limit'] = new_rule.decoder_memory_limit
        new_limits[new_rule.test.pk]['encoder_time_limit'] = new_rule.encoder_time_limit
        new_limits[new_rule.test.pk]['decoder_time_limit'] = new_rule.decoder_time_limit

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

    problem_instance = env['problem_instance_id']
    if 'tests_subset' in env['extra_args']:
        tests = list(EncdecTest.objects.in_bulk(env['extra_args']['tests_subset']).values())
    else:
        tests = EncdecTest.objects.filter(
            problem_instance__id=problem_instance, is_active=True
        )

    if env['is_rejudge']:
        submission = env['submission_id']
        rejudge_type = env['extra_args'].setdefault('rejudge_type', 'FULL')
        tests_to_judge = env['extra_args'].setdefault('tests_to_judge', [])
        test_reports = EncdecTestReport.objects.filter(
            submission_report__submission__id=submission,
            submission_report__status='ACTIVE',
        )
        tests_used = [report.test_name for report in test_reports]
        if rejudge_type == 'NEW':
            tests_to_judge = [
                t.name
                for t in EncdecTest.objects.filter(
                    problem_instance__id=problem_instance, is_active=True
                ).exclude(name__in=tests_used)
            ]
        elif rejudge_type == 'JUDGED':
            tests = EndecTest.objects.filter(
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
        test_env['input_file'] = django_to_filetracker_path(test.input_file)
        test_env['hint_file'] = django_to_filetracker_path(test.hint_file)
        test_env['kind'] = test.kind
        test_env['group'] = test.group or test.name
        test_env['max_score'] = test.max_score
        test_env['order'] = test.order
        if test.encoder_time_limit:
            test_env['encoder_time_limit'] = new_limits[test.pk]['encoder_time_limit']
        if test.decoder_time_limit:
            test_env['decoder_time_limit'] = new_limits[test.pk]['decoder_time_limit']
        if test.encoder_memory_limit:
            test_env['encoder_memory_limit'] = new_limits[test.pk]['encoder_memory_limit']
        if test.decoder_memory_limit:
            test_env['decoder_memory_limit'] = new_limits[test.pk]['decoder_memory_limit']
        test_env['to_judge'] = False
        env['tests'][test.name] = test_env

    for test in tests_to_judge:
        env['tests'][test]['to_judge'] = True
    return env



@_skip_on_compilation_error
def run_encoder(env, kind=None, **kwargs):
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
      * ``encoder_results``: a dictionary, mapping test names into
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
        job = {}
        job['job_type'] = (env.get('exec_mode', '') + '-encdec-encoder-exec').lstrip('-')
        job['in_file'] = test_env['input_file']
        job['hint_file'] = test_env['hint_file']
        if kind == 'INITIAL' or kind == 'EXAMPLE':
            job['task_priority'] = EXAMPLE_TEST_TASK_PRIORITY
        elif env['submission_kind'] == 'TESTRUN':
            job['task_priority'] = TESTRUN_TEST_TASK_PRIORITY
        else:
            job['task_priority'] = DEFAULT_TEST_TASK_PRIORITY
        job['exe_file'] = env['compiled_file']
        job['exec_info'] = env['exec_info']
        if 'encoder_memory_limit' in test_env:
            job['exec_memory_limit'] = test_env['encoder_memory_limit']
        if 'encoder_time_limit' in test_env:
            job['exec_time_limit'] = test_env['encoder_time_limit']
        job['chn_file'] = env['channel']
        job['out_file'] = _make_filename(env, test_name + '.enc')
        test_env['encoder_output'] = job['out_file']
        test_env['input_for_decoder'] = job['input_for_decoder'] \
                = _make_filename(env, test_name + '.dec_in')
        test_env['input_for_checker'] = job['input_for_checker'] \
                = _make_filename(env, test_name + '.chk_in')
        job['upload_out'] = True
        job['untrusted_checker'] = env['untrusted_checker']
        job['max_score'] = test_env['max_score']
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
def run_decoder(env, kind=None, **kwargs):
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
      * ``decoder_results``: a dictionary, mapping test names into
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
    encoder_failed = []
    for test_name, test_env in env['tests'].items():
        if kind and test_env['kind'] != kind:
            continue
        if not test_env['to_judge']:
            not_to_judge.append(test_name)
            continue
        if env['encoder_results'][test_name]['result_code'] != 'OK':
            encoder_failed.append(test_name)
            continue
        job = {}
        job['job_type'] = (env.get('exec_mode', '') + '-encdec-decoder-exec').lstrip('-')
        job['original_input_file'] = test_env['input_file']
        job['in_file'] = test_env['input_for_decoder']
        job['hint_file'] = test_env['hint_file']
        job['channel_output_file'] = test_env['input_for_checker']
        if kind == 'INITIAL' or kind == 'EXAMPLE':
            job['task_priority'] = EXAMPLE_TEST_TASK_PRIORITY
        elif env['submission_kind'] == 'TESTRUN':
            job['task_priority'] = TESTRUN_TEST_TASK_PRIORITY
        else:
            job['task_priority'] = DEFAULT_TEST_TASK_PRIORITY
        job['exe_file'] = env['compiled_file']
        job['exec_info'] = env['exec_info']
        if 'decoder_memory_limit' in test_env:
            job['exec_memory_limit'] = test_env['decoder_memory_limit']
        if 'decoder_time_limit' in test_env:
            job['exec_time_limit'] = test_env['decoder_time_limit']
        job['chk_file'] = env['checker']
        job['out_file'] = _make_filename(env, test_name + '.out')
        if env.get('save_outputs'):
            job['upload_out'] = True
        job['untrusted_checker'] = env['untrusted_checker']
        job['max_score'] = test_env['max_score']
        jobs[test_name] = job
    extra_args = env.get('sioworkers_extra_args', {}).get(kind, {})
    env['workers_jobs'] = jobs
    env['workers_jobs.extra_args'] = extra_args
    env['workers_jobs.not_to_judge'] = not_to_judge
    env['workers_jobs.encoder_failed'] = encoder_failed
    return transfer_job(
        env,
        'oioioi.sioworkers.handlers.transfer_job',
        'oioioi.sioworkers.handlers.restore_job',
    )


@_skip_on_compilation_error
def run_encoder_end(env, **kwargs):
    del env['workers_jobs']
    not_to_judge = env['workers_jobs.not_to_judge']
    del env['workers_jobs.not_to_judge']
    jobs = env['workers_jobs.results']
    del env['workers_jobs.results']
    env.setdefault('encoder_results', {})
    for test_name, result in jobs.items():
        env['encoder_results'].setdefault(test_name, {}).update(result)
    for test_name in not_to_judge:
        env['encoder_results'].setdefault(test_name, {}).update({})
    return env


@_skip_on_compilation_error
def run_decoder_end(env, **kwargs):
    del env['workers_jobs']
    not_to_judge = env['workers_jobs.not_to_judge']
    del env['workers_jobs.not_to_judge']
    encoder_failed = env['workers_jobs.encoder_failed']
    del env['workers_jobs.encoder_failed']
    jobs = env['workers_jobs.results']
    del env['workers_jobs.results']
    env.setdefault('decoder_results', {})
    for test_name, result in jobs.items():
        env['decoder_results'].setdefault(test_name, {}).update(result)
    for test_name in not_to_judge:
        env['decoder_results'].setdefault(test_name, {}).update({})
    for test_name in encoder_failed:
        env['decoder_results'].setdefault(test_name, {}).update({
            'skipped': True,
            'score': None,
            'max_score': None,
            'result_code': 'SKIP'
        })
    return env


@_skip_on_compilation_error
def grade_encoder(env, **kwargs):
    """Grades tests using a scoring function.

    The ``env['test_scorer']``, which is used by this ``Handler``,
    should be a path to a function which gets test definition (e.g.  a
    ``env['tests'][test_name]`` dict) and test run result (e.g.  a
    ``env['encoder_results'][test_name]`` dict) and returns a score
    (instance of some subclass of
    :class:`~oioioi.contests.scores.ScoreValue`) and a status.

    Used ``environ`` keys:
      * ``tests``
      * ``encoder_results``
      * ``test_scorer``

    Produced ``environ`` keys:
      * `score`, `max_score` and `status` keys in ``env['test_result']``
    """

    tests = env['tests']
    for test_name, test_result in env['encoder_results'].items():
        if not tests[test_name]['to_judge']:
            report = EncdecTestReport.objects.get(
                submission_report__submission__id=env['submission_id'],
                submission_report__status='ACTIVE',
                test_name=test_name,
            )
            test_result['status'] = report.encoder_status
            test_result['time_used'] = report.encoder_time_used
    return env


@_skip_on_compilation_error
def grade_decoder(env, **kwargs):
    """Grades tests using a scoring function.

    The ``env['test_scorer']``, which is used by this ``Handler``,
    should be a path to a function which gets test definition (e.g.  a
    ``env['tests'][test_name]`` dict) and test run result (e.g.  a
    ``env['decoder_results'][test_name]`` dict) and returns a score
    (instance of some subclass of
    :class:`~oioioi.contests.scores.ScoreValue`) and a status.

    Used ``environ`` keys:
      * ``tests``
      * ``decoder_results``
      * ``test_scorer``

    Produced ``environ`` keys:
      * `score`, `max_score` and `status` keys in ``env['test_result']``
    """

    test_scorer = import_string(env.get('test_scorer') or settings.DEFAULT_TEST_SCORER)
    print(repr(test_scorer))
    tests = env['tests']
    encoder_results = env['encoder_results']
    for test_name, decoder_result in env['decoder_results'].items():
        if tests[test_name]['to_judge']:
            used_result = decoder_result
            if decoder_result.get('skipped', False):
                # Must have failed, so will not succeed
                used_result = encoder_results[test_name]
            # TODO: combine the two
            print('UR', used_result)
            score, max_score, status = test_scorer(tests[test_name], used_result)
            assert isinstance(score, (type(None), ScoreValue))
            assert isinstance(max_score, (type(None), ScoreValue))
            decoder_result['score'] = score and score.serialize()
            decoder_result['max_score'] = max_score and max_score.serialize()
            decoder_result['status'] = status
        else:
            report = EncdecTestReport.objects.get(
                submission_report__submission__id=env['submission_id'],
                submission_report__status='ACTIVE',
                test_name=test_name,
            )
            score = report.score
            max_score = report.max_score
            status = report.decoder_status
            time_used = report.decoder_time_used
            decoder_result['score'] = score and score.serialize()
            decoder_result['max_score'] = max_score and max_score.serialize()
            decoder_result['status'] = status
            decoder_result['time_used'] = time_used
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
      * ``encoder_results``
      * ``group_scorer``

    Produced ``environ`` keys:
      * `score`, `max_score` and `status` keys in ``env['group_results']``
    """

    test_results = defaultdict(dict)
    for test_name, test_result in env['decoder_results'].items():
        test = env['tests'][test_name]
        group_name = test['group']
        test_results[group_name][test_name] = {
            'score': test_result['score'],
            'max_score': test_result['max_score'],
            'order': test['order'],
            'status': test_result['status']
        }

    group_scorer = import_string(env.get('group_scorer', settings.DEFAULT_GROUP_SCORER))
    env.setdefault('group_results', {})
    for group_name, results in test_results.items():
        if group_name in env['group_results']:
            continue
        score, max_score, status = group_scorer(results)
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
        * ``decoder_results``
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

    encoder_results = env.get('encoder_results', {})
    decoder_results = env.get('decoder_results', {})
    for test_name, decoder_result in decoder_results.items():
        encoder_result = encoder_results[test_name]
        test = tests[test_name]
        if 'report_id' in decoder_result:
            continue
        test_report = EncdecTestReport(submission_report=submission_report)
        test_report.test_id = test.get('id')
        test_report.test_name = test_name
        test_report.test_group = test['group']
        test_report.test_encoder_time_limit = test['encoder_time_limit']
        test_report.test_decoder_time_limit = test['decoder_time_limit']
        test_report.max_score = decoder_result['max_score']
        test_report.score = decoder_result['score'] if save_scores else None
        test_report.encoder_status = encoder_result['result_code']
        test_report.decoder_status = decoder_result['result_code']
        test_report.encoder_time_used = encoder_result['time_used']
        test_report.decoder_time_used = decoder_result.get('time_used', 0)

        comment = decoder_result.get('result_string', '')
        if comment.lower() in ['ok', 'time limit exceeded']:  # Annoying
            comment = ''
        test_report.comment = Truncator(comment).chars(
            EncdecTestReport._meta.get_field('comment').max_length
        )
        if env.get('save_outputs', False):
            test_report.output_file = filetracker_to_django_file(decoder_result['out_file'])
        test_report.save()
        decoder_result['report_id'] = test_report.id

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


@transaction.atomic
def fill_outfile_in_existing_test_reports(env, **kwargs):
    """Fill output files into existing test reports that are not directly
    related to present submission. Also change status of UserOutGenStatus
    object to finished.

    Used ``environ`` keys:
        * ``extra_args`` dictionary with ``submission_report`` object
        * ``decoder_results``
    """
    if 'submission_report_id' not in env['extra_args']:
        logger.info('No submission_report given to fill tests outputs')
        return env

    submission_report_id = env['extra_args']['submission_report_id']
    submission_report = SubmissionReport.objects.get(id=submission_report_id)
    test_reports = EncdecTestReport.objects.filter(submission_report=submission_report)
    decoder_results = env.get('decoder_results', {})

    for test_name, result in decoder_results.items():
        try:
            testreport = test_reports.get(test_name=test_name)
        except (EncdecTestReport.DoesNotExist, EncdecTestReport.MultipleObjectsReturned):
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
