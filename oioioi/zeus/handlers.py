import json
import logging
import socket
from smtplib import SMTPException

from django.core.files.base import ContentFile
from django.core.mail import mail_admins
from django.db import transaction, IntegrityError
from django.forms.models import model_to_dict

from oioioi.base.utils import get_object_by_dotted_name, naturalsort_key
from oioioi.problems.models import Problem
from oioioi.programs.handlers import _make_base_report
from oioioi.programs.models import ProgramSubmission, Test
from oioioi.programs.utils import slice_str
from oioioi.zeus.backends import get_zeus_server
from oioioi.zeus.models import ZeusTestRunReport, ZeusAsyncJob, \
        ZeusTestRunProgramSubmission, ZeusProblemData


DEFAULT_METADATA_DECODER = 'oioioi.zeus.handlers.from_csv_metadata'
logger = logging.getLogger(__name__)


def testrun_metadata(_metadata):
    """Mock metadata decoder for using with testrun."""
    return {
        'name': 'test',
        'group': '',
        'max_score': 0,
    }


def from_csv_metadata(metadata):
    data = metadata.split(',')
    test, group, max_score = [f.strip() for f in data]
    if group == '':
        group = test
    return {
        'name': test,
        'group': group,
        'max_score': int(max_score),
    }


@transaction.atomic
def submit_job(env, kind=None, **kwargs):
    """Submits the job to Zeus for given ``kind``.

       Used ``environ`` keys:
         * ``submission_id``
         * ``language``
         * ``zeus_id``
         * ``zeus_problem_id``

       Altered ``environ`` keys:
          * ``zeus_check_uids`` - dictionary mapping grading kind to
                                 Zeus's ``check_uid``
    """
    assert kind is not None
    zeus = get_zeus_server(env['zeus_id'])
    ps = ProgramSubmission.objects.get(id=env['submission_id'])
    check_uid = zeus.send_regular(kind=kind, source_file=ps.source_file,
            zeus_problem_id=env['zeus_problem_id'], language=env['language'])
    env.setdefault('zeus_check_uids', {})[kind] = check_uid
    return env


@transaction.atomic
def submit_testrun_job(env, **kwargs):
    """Submits the testrun job to Zeus.

       Used ``environ`` keys:
         * ``submission_id``
         * ``language``
         * ``zeus_id``
         * ``zeus_problem_id``

       Altered ``environ`` keys:
          * ``zeus_check_uids`` - dictionary mapping grading kind to
                                 Zeus's ``check_uid``
    """
    zeus = get_zeus_server(env['zeus_id'])
    ps = ZeusTestRunProgramSubmission.objects.get(id=env['submission_id'])
    check_uid = zeus.send_testrun(source_file=ps.source_file,
            zeus_problem_id=env['zeus_problem_id'], language=env['language'],
            input_file=ps.input_file, library_file=ps.library_file)
    env.setdefault('zeus_check_uids', {})['TESTRUN'] = check_uid
    return env


@transaction.atomic
def save_env(env, kind=None, **kwargs):
    """Saves asynchronous job's environment in the database
       for later retrieval, clearing current recipe. This allows to submit
       results from another process, without having evalmgr actively waiting.

       This handler will save current job's status in
       :class:`~oioioi.zeus.models.ZeusAsyncJob` objects for later
       retrieval in results fetcher. After that, the job can be simply
       continued with ``evalmgr.evalmgr_job.delay(zeus_async_job.environ)``.
       The ``zeus_async_job.check_uid`` is taken from
       ``environ['zeus_check_uids`][kind]``.

       If results happen to be already in db, job is not suspended.

       Used ``environ`` keys:
         * ``recipe``
         * ``zeus_check_uids`` - asynchronous jobs objects

       Altered ``environ`` keys:
         * ``recipe``
    """
    assert kind is not None
    check_uid = env['zeus_check_uids'][kind]
    try:
        async_job, created = ZeusAsyncJob.objects.select_for_update() \
                .get_or_create(check_uid=check_uid)
    except IntegrityError:
        # This should never happen.
        logger.error("IntegrityError while saving job for uid %s", check_uid,
                     exc_info=True)
        logger.error("Environ:\n%s", json.dumps(env))
        raise
    if created:
        async_job.environ = json.dumps(env)
        async_job.save()
        env['recipe'] = []
    else:
        assert not async_job.resumed, ("Oops, got uid %s twice?" % check_uid)
        logger.info("Resuming job %s from save_env", check_uid)
        saved_env = json.loads(async_job.environ)
        env.setdefault('zeus_results', [])
        env['zeus_results'].extend(saved_env['zeus_results'])
        async_job.resumed = True
        async_job.save()
    return env


def import_results(env, kind=None, map_to_kind=None, **kwargs):
    """Imports the results returned by Zeus.

       If ``kind`` is specified, it will only look for results with given kind.
       If ``map_to_kind`` is specified, all matching tests will be imported
       with kind replaced with ``map_to_kind``.

       The ``env['zeus_metadata_decoder']``, which is used by this ``Handler``,
       should be a path to a function which gets Zeus metadata for test
       (e.g.  a ``env['zeus_results'][0]['metadata']`` string) and returns
       a dictionary which will be a base for ``test`` information
       (at least containing keys ``name``, ``group`` and ``max_score``
       defined as below).

       Used ``environ`` keys:
         * ``zeus_results`` - populated by results fetcher

       Produced ``environ`` keys:
          * env['compilation_result'] - may be OK if the file compiled
                                        successfully or CE otherwise.
          * env['compilation_message'] - contains compiler stdout and stderr

          * ``tests`` - a dictionary mapping test names into
            dictionaries with following keys:

            ``name``
              test name
            ``kind``
              kind of the test (EXAMPLE, NORMAL)
            ``group``
              group the test belongs to
            ``max_score``
              maximum score the user can get for this test
            ``exec_time_limit``
              time limit for the test (in ms)
            ``exec_memory_limit``
              memory limit for the test (in KiB)
            ``zeus_metadata``
              raw metadata for the test as returned by Zeus

          * ``test_results`` - a dictionary, mapping test names into
            dictionaries with the following keys:

              ``result_code``
                test status: OK, WA, RE, ...
              ``result_string``
                detailed supervisor information (for example, where the
                required and returned outputs differ)
              ``time_used``
                total time used, in milliseconds
              ``zeus_test_result``
                raw result returned by Zeus
    """
    zeus_results = [r for r in env['zeus_results'] if r['report_kind'] == kind]
    # Assuming compilation statuses are consistent
    env['compilation_result'] = \
            'OK' if zeus_results[0].get('compilation_successful') else 'CE'
    env['compilation_message'] = zeus_results[0].get('compilation_message')

    decoder = get_object_by_dotted_name(env.get('zeus_metadata_decoder')
            or DEFAULT_METADATA_DECODER)

    tests = env.setdefault('tests', {})
    test_results = env.setdefault('test_results', {})
    for result in zeus_results:
        test = decoder(result['metadata'])
        error = "Not enough data decoded from: %s" % result['metadata']
        assert 'name' in test, error
        assert 'group' in test, error
        assert 'max_score' in test, error
        if test['name'] in test_results:
            continue

        test.update({
            'zeus_metadata': result['metadata'],
            'kind': map_to_kind if map_to_kind else result['report_kind'],
            'exec_time_limit': result['time_limit_ms'],
            'exec_memory_limit': result['memory_limit_byte'] / 1024,
        })
        tests[test['name']] = test

        test_results[test['name']] = {
            'result_code': result['status'],
            'result_string': result['result_string'],
            'time_used': result['execution_time_ms'],
            'zeus_test_result': result,
        }

    return env


@transaction.atomic
def make_zeus_testrun_report(env, **kwargs):
    """Builds entities for Zeus-testrun reports in a database.

       Used ``environ`` keys:
           * ``tests``
           * ``test_results``
           * ``status``
           * ``score``
           * ``compilation_result``
           * ``compilation_message``
           * ``submission_id``

       Produced ``environ`` keys:
           * ``report_id``: id of the produced
             :class:`~oioioi.contests.models.SubmissionReport`
    """
    _submission, submission_report = _make_base_report(env, 'TESTRUN')

    if env['compilation_result'] != 'OK':
        return env

    test_name = env['tests'].keys()[0]
    test = env['tests'][test_name]
    test_result = env['test_results'][test_name]
    zeus_result = test_result['zeus_test_result']

    comment = test_result.get('result_string', '')
    if comment.lower() == 'ok':  # Annoying
        comment = ''

    testrun_report = ZeusTestRunReport(submission_report=submission_report)
    testrun_report.status = env['status']
    testrun_report.comment = \
        slice_str(comment, ZeusTestRunReport._meta
        .get_field('comment').max_length)
    testrun_report.time_used = test_result['time_used']
    testrun_report.test_time_limit = test.get('exec_time_limit')
    testrun_report.full_out_size = zeus_result['stdout_size']
    # The server to download from: submission.problem_instance.problem
    testrun_report.full_out_handle = zeus_result['stdout_uid']
    # Output truncated to first 10kB
    testrun_report.output_file.save('out', ContentFile(zeus_result['stdout']))
    testrun_report.save()
    return env


@transaction.atomic
def save_zeus_data(env):
    problem = Problem.objects.get(id=env['problem_id'])
    problem_data, _created = ZeusProblemData.objects \
            .get_or_create(problem=problem)
    problem_data.zeus_id = env['zeus_id']
    problem_data.zeus_problem_id = env['zeus_problem_id']
    problem_data.save()
    return env


@transaction.atomic
def update_problem_tests_set(env, kind, **kwargs):
    """Creates or updates problem :class:`oioioi.programs.models.Test` objects
       basing on ``env['tests']`` dict.

       Sends email to all admins when tests set differ.

       Considers only tests with given ``kind``.

       Used ``environ`` keys:
           * ``tests``
           * ``zeus_problem_id``
           * ``zeus_id``
    """

    data = ZeusProblemData.objects.get(zeus_id=env['zeus_id'],
                                       zeus_problem_id=env['zeus_problem_id'])
    problem = data.problem

    env_tests = {key: value for key, value in env['tests'].iteritems()
                 if value['kind'] == kind}
    test_names = env_tests.keys()

    new_tests = []
    deleted_tests = []
    updated_tests = []
    tests_set_changed = False
    exclude = ['input_file', 'output_file']

    for i, name in enumerate(sorted(test_names, key=naturalsort_key)):
        updated = False
        test = env_tests[name]
        instance, created = Test.objects.select_for_update().get_or_create(
            problem=problem, name=name)
        env['tests'][name]['id'] = instance.id
        old_dict = model_to_dict(instance, exclude=exclude)

        for attr in ['kind', 'group', 'max_score']:
            if getattr(instance, attr) != test[attr]:
                setattr(instance, attr, test[attr])
                updated = True

        if instance.time_limit != test['exec_time_limit']:
            instance.time_limit, updated = test['exec_time_limit'], True
        if instance.memory_limit != test['exec_memory_limit']:
            instance.memory_limit = test['exec_memory_limit']
            updated = True

        order = i
        if kind == 'EXAMPLE':
            order = -len(test_names) + i
        if instance.order != order:
            instance.order, updated = order, True

        if updated or created:
            tests_set_changed = True
            instance.save()
            new_dict = model_to_dict(instance, exclude=exclude)
            if created:
                new_tests.append((name, new_dict))
            else:
                updated_tests.append((name, old_dict, new_dict))

    # Delete nonexistent tests
    for test in Test.objects.filter(problem=problem, kind=kind) \
            .exclude(name__in=test_names):
        deleted_tests.append((test.name, model_to_dict(test, exclude=exclude)))
        tests_set_changed = True
        test.delete()

    if tests_set_changed:
        logger.info("%s: %s tests set changed", problem.short_name, kind)

        title = "Zeus problem %s: %s tests set changed" \
                % (problem.short_name, kind)
        content = ["%s tests set for zeus problem %s has changed:"
                   % (kind, problem.short_name)]
        for name, old_dict in new_tests:
            content.append("    + added test %s: %s" % (name, old_dict))
        for name, old_dict in deleted_tests:
            content.append("    - deleted test %s: %s" % (name, old_dict))
        for name, old_dict, new_dict in updated_tests:
            content.append("    * changed test %s: %s -> %s" %
                           (name, old_dict, new_dict))
        try:
            mail_admins(title, '\n'.join(content))
        except (socket.error, SMTPException):
            logger.error("An error occurred while sending email.\n%s",
                         exc_info=True)
        logger.debug('Sent mail: ' + '\n'.join(content))

    return env
