from django.db import transaction
from django.utils.text import Truncator

from oioioi.filetracker.client import get_client
from oioioi.filetracker.utils import (
    django_to_filetracker_path,
    filetracker_to_django_file,
)
from oioioi.programs.handlers import (
    _get_submission_or_skip,
    _make_base_report,
    _skip_on_compilation_error,
)
from oioioi.testrun.models import TestRunConfig, TestRunProgramSubmission, TestRunReport


@_skip_on_compilation_error
@transaction.atomic
@_get_submission_or_skip(submission_class=TestRunProgramSubmission)
def make_test(env, submission, **kwargs):
    """Creates a testcase *test* from the user input and converts it to
    evaluation environment.

    Used ``environ`` keys:
      * ``submission_id``
      * ``problem_id``

    Produced ``environ`` keys:
       * ``tests``: a dictionary mapping test names to test envs
    """
    assert submission.kind == 'TESTRUN'
    config = TestRunConfig.objects.get(problem_instance__problem__id=env['problem_id'])

    test_env = {}
    test_env['name'] = 'test'
    test_env['in_file'] = django_to_filetracker_path(submission.input_file)
    test_env['out_file'] = '/testruns/%s/%d/%s-out' % (
        env['contest_id'],
        env['submission_id'],
        env['job_id'],
    )
    test_env['to_judge'] = True
    if config.time_limit:
        test_env['exec_time_limit'] = config.time_limit
    if config.memory_limit:
        test_env['exec_mem_limit'] = config.memory_limit

    env['tests'] = {'test': test_env}

    return env


def grade_submission(env, **kwargs):
    """Grades submission: fills fields used by common postprocessors.

    This `Handler` gets submission status from *test* test result.

    Used ``environ`` keys:
        * ``test_results``

    Produced ``environ`` keys:
        * ``status``
        * ``score``
        * ``max_score``
    """
    env['score'] = None
    env['max_score'] = None

    if env.get('compilation_result', 'OK') != 'OK':
        env['status'] = 'CE'
    elif env['test_results']['test']['result_code'] == 'OK':
        env['status'] = 'TESTRUN_OK'
    else:
        env['status'] = env['test_results']['test']['result_code']

    return env


@transaction.atomic
def make_report(env, **kwargs):
    """Builds entities for testrun reports in a database.

    Used ``environ`` keys:
        * ``tests``
        * ``test_results``
        * ``status``
        * ``score``
        * ``compilation_result``
        * ``compilation_message``

    Produced ``environ`` keys:
        * ``report_id``: id of the produced
          :class:`~oioioi.contests.models.SubmissionReport`
    """
    _submission, submission_report = _make_base_report(env, 'TESTRUN')

    if env['compilation_result'] != 'OK':
        return env

    test = env['tests']['test']
    test_result = env['test_results']['test']

    comment = test_result.get('result_string', '')
    if comment.lower() == 'ok':  # Annoying
        comment = ''

    testrun_report = TestRunReport(submission_report=submission_report)
    testrun_report.status = env['status']
    max_comment_length = TestRunReport._meta.get_field('comment').max_length
    testrun_report.comment = (comment[:max_comment_length - 1] + '…') if len(comment) > max_comment_length else comment
    testrun_report.time_used = test_result['time_used']
    testrun_report.test_time_limit = test.get('exec_time_limit')
    testrun_report.output_file = filetracker_to_django_file(test_result['out_file'])
    testrun_report.save()

    return env


def delete_output(env, **kwargs):
    if 'out_file' in env.get('test_results', {}).get('test', {}):
        get_client().delete_file(env['test_results']['test']['out_file'])
    return env
