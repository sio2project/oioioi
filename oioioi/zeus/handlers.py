import logging
import random
import socket
from smtplib import SMTPException

from django.conf import settings
from django.core.mail import mail_admins
from django.core.urlresolvers import reverse
from django.db import transaction
from django.forms.models import model_to_dict
from django.utils.module_loading import import_string

from oioioi import evalmgr
from oioioi.base.utils import naturalsort_key
from oioioi.contests.handlers import _get_submission_or_skip
from oioioi.programs.handlers import _skip_on_compilation_error
from oioioi.programs.models import ProgramSubmission, Test
from oioioi.zeus.backends import get_zeus_server
from oioioi.zeus.models import ZeusProblemData
from oioioi.zeus.utils import zeus_url_signature


DEFAULT_METADATA_DECODER = 'oioioi.zeus.handlers.from_csv_metadata'
logger = logging.getLogger(__name__)


def from_csv_metadata(metadata):
    try:
        data = metadata.split(',')
        test, group, max_score = [f.strip() for f in data]
    except StandardError:
        test, group, max_score = \
            ('unknown-%d' % random.randint(1, 100000)), '', '1'
    if group == '':
        group = test
    return {
        'name': test,
        'group': group,
        'max_score': int(max_score),
    }


@_skip_on_compilation_error
@transaction.atomic
@_get_submission_or_skip(submission_class=ProgramSubmission)
def submit_job(env, submission, kind):
    """Recipe handler that sends the job to Zeus.
    """
    with submission.source_file as f:
        source_code = f.read()
    return evalmgr.transfer_job(env,
            'oioioi.zeus.handlers.transfer_job',
            'oioioi.zeus.handlers.restore_job',
            transfer_kwargs={'kind': kind, 'source_code': source_code})


def transfer_job(env, kind, source_code):
    """"Sends the job to Zeus for given ``kind``.

        Used ``env`` keys:
          * ``submission_id``
          * ``language``
          * ``saved_environ_id``
          * ``zeus_problem_id``
          * ``zeus_id``
    """
    # Env is already saved in evalmgr, use saved_environ_id to
    # identify results.
    zeus = get_zeus_server(env['zeus_id'])
    saved_environ_id = env['saved_environ_id']

    return_url = settings.ZEUS_PUSH_GRADE_CALLBACK_URL + reverse(
        'zeus_push_grade_callback',
        kwargs={
            'saved_environ_id': saved_environ_id,
            'signature': zeus_url_signature(saved_environ_id)
        }
    )

    zeus.send_regular(kind=kind,
            return_url=return_url,
            source_code=source_code,
            zeus_problem_id=env['zeus_problem_id'],
            language=env['language'],
            submission_id=['submission_id'])


def restore_job(env, results_env):
    env['compilation_result'] = results_env['compilation_result']
    env['compilation_message'] = results_env['compilation_message']
    env.setdefault('zeus_results', []).extend(results_env['reports'])
    return env


MAP_VERDICT_TO_STATUS = {
    "OK": "OK",
    "Wrong answer": "WA",
    "Time limit exceeded": "TLE",
    "Runtime error": "RE",
    "Rule violation": "RV",
    "Output limit exceeded": "OLE",
    "Messages size limit exceeded": "MSE",
    "Messages count limit exceeded": "MCE",
    "Compilation error": "CE"
}


def import_results(env, **kwargs):
    """Imports the results returned by Zeus.

       The ``env['zeus_metadata_decoder']``, which is used by this ``Handler``,
       should be a path to a function which gets Zeus metadata for test
       (e.g.  a ``env['zeus_results'][0]['metadata']`` string) and returns
       a dictionary which will be a base for ``test`` information
       (at least containing keys ``name``, ``group`` and ``max_score``
       defined as below).

       Used ``environ`` keys:
         * ``zeus_results`` - retrieved from Zeus callback

         * ``compilation_result`` - may be OK if the file compiled
                                    successfully or CE otherwise.

       Produced ``environ`` keys:

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
    zeus_results = env['zeus_results']

    if env['compilation_result'] != 'OK':
        return env

    decoder = import_string(env.get('zeus_metadata_decoder')
            or DEFAULT_METADATA_DECODER)

    tests = env.setdefault('tests', {})
    test_results = env.setdefault('test_results', {})
    for order, result in enumerate(zeus_results):
        test = decoder(result['metadata'])
        error = "Not enough data decoded from: %s" % result['metadata']
        assert 'name' in test, error
        assert 'group' in test, error
        assert 'max_score' in test, error
        if test['name'] in test_results:
            continue

        if test['group'] == '0':
            kind = 'EXAMPLE'
        else:
            kind = 'NORMAL'

        test.update({
            'zeus_metadata': result['metadata'],
            'kind': kind,
            'exec_time_limit': result['time_limit_ms'],
            'exec_memory_limit': result['memory_limit_byte'] / 1024,
            'nodes': result.get('nof_nodes'),
            'to_judge': True,
        })
        tests[test['name']] = test

        test_result = {
            'result_code': MAP_VERDICT_TO_STATUS.get(result['verdict'], 'SE'),
            'result_string': '',
            'time_used': result['runtime'],
            'zeus_test_result': result,
            'order': order,
        }

        # Fix/hack? for missing time_limit
        if test_result['time_used'] is None or test_result['time_used'] == '':
            test_result['time_used'] = test['exec_time_limit'] \
                    if test_result['result_code'] == 'TLE' else 0

        test_results[test['name']] = test_result

    return env


@_skip_on_compilation_error
@transaction.atomic
def update_problem_tests_set(env, kind, **kwargs):
    """Creates or updates problem :class:`oioioi.programs.models.Test` objects
       basing on ``env['tests']`` dict.

       Sends email to all admins when tests set differ.

       Considers only tests with given ``kind``.

       Used ``environ`` keys:
           * ``problem_id``
           * ``tests``
           * ``zeus_problem_id``
           * ``zeus_id``
    """

    if env['compilation_result'] != 'OK':
        return

    data = ZeusProblemData.objects.get(problem_id=env['problem_id'],
                                       zeus_id=env['zeus_id'],
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
            problem_instance=problem.main_problem_instance, name=name)
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
    for test in Test.objects.filter(
            problem_instance=problem.main_problem_instance, kind=kind) \
            .exclude(name__in=test_names):
        deleted_tests.append((test.name, model_to_dict(test, exclude=exclude)))
        tests_set_changed = True
        test.delete()

    if tests_set_changed:
        # NOTE one could be tempted to call
        # update_all_probleminstances_after_reupload(problem) here
        # but this would be a bad idea - the tests are 'changed' at least
        # when the first submission to the problem gets judged - before
        # we have no information about them.
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
