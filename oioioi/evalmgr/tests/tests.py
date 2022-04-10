import copy
import os.path
import uuid

from django.db import transaction
from django.test.utils import override_settings
from django.urls import reverse

from oioioi.base.tests import TestCase
from oioioi.contests.models import Contest, Submission
from oioioi.evalmgr.models import QueuedJob, SavedEnviron
from oioioi.evalmgr.tasks import create_environ, delay_environ, transfer_job
from oioioi.evalmgr.utils import mark_job_state
from oioioi.filetracker.client import get_client
from oioioi.programs.controllers import ProgrammingContestController
from oioioi.sioworkers.jobs import run_sioworkers_job


def delay_environ_wrapper(*args, **kwargs):
    with transaction.atomic():
        result = delay_environ(*args, **kwargs)
    return result


hunting = [
    ('Prepare guns', 'oioioi.evalmgr.tests.tests.prepare_handler'),
    ('Hunt', 'oioioi.evalmgr.tests.tests.hunting_handler', {'animal': 'hedgehog'}),
    ('Rest', 'oioioi.evalmgr.tests.tests.rest_handler'),
]


class HuntingException(Exception):
    pass


def hunting_handler(env, **kwargs):
    if kwargs['animal'] == 'hedgehog' and env['area'] == 'forest' and env['prepared']:
        env['result'] = 'Hedgehog hunted.'
    elif kwargs['animal'] == 'hedgehog' and env['area'] == 'elevator':
        raise HuntingException('Its prohibited to kill hedgehogs in elevator.')
    elif env['area'] == 'blackhole':
        return None
    else:
        env['result'] = 'Epic fail.'
    return env


def prepare_handler(env, **kwargs):
    env['prepared'] = True
    return env


def rest_handler(env, **kwargs):
    env['output'] = env['result']
    return env


class TestLocalJobs(TestCase):
    def test_evalmgr_job(self):
        env = create_environ()
        env.update(dict(recipe=hunting, area='forest'))
        env = delay_environ_wrapper(env).get()
        self.assertEqual('Hedgehog hunted.', env['output'])

    def test_cascade_job(self):
        env = create_environ()
        env.update(dict(recipe=hunting, area='forest'))
        env = delay_environ_wrapper(env).get()
        self.assertEqual('Hedgehog hunted.', env['output'])

    def test_multiple_jobs(self):
        city_result = delay_environ_wrapper(
            dict(job_id=42, recipe=hunting, area='city')
        )
        forest_result = delay_environ_wrapper(
            dict(job_id=43, recipe=hunting, area='forest')
        )
        jungle_result = delay_environ_wrapper(
            dict(job_id=44, recipe=hunting, area='jungle')
        )
        self.assertEqual('Hedgehog hunted.', forest_result.get()['output'])
        self.assertEqual('Epic fail.', city_result.get()['output'])
        self.assertEqual('Epic fail.', jungle_result.get()['output'])


def upload_source(env, **kwargs):
    fc = get_client()
    fc.put_file(env['remote_source_file'], env['local_source_file'])
    return env


def compile_source(env, **kwargs):
    env.update(
        dict(
            source_file=env['remote_source_file'],
            out_file=env['binary_file'],
            compiler='system-gcc',
            job_type='compile',
        )
    )
    return run_sioworkers_job(env)


def upload_inout(env, **kwargs):
    fc = get_client()
    env.update({'in_file': env['remote_in_file'], 'hint_file': env['remote_out_file']})
    fc.put_file(env['remote_in_file'], env['local_in_file'])
    fc.put_file(env['remote_out_file'], env['local_out_file'])
    return env


def run(env, **kwargs):
    env.update(
        dict(exe_file=env['binary_file'], check_output=True, job_type='unsafe-exec')
    )
    return run_sioworkers_job(env)


class SioworkersBackend(object):
    def run_job(self, env):
        env = copy.deepcopy(env)
        if env['job_type'] == 'compile':
            return env
        elif env['job_type'] == 'unsafe-exec':
            if 'wrong' in env['source_file']:
                env['result_code'] = 'WA'
            else:
                env['result_code'] = 'OK'
            return env


def _uuid():
    return uuid.uuid4().hex


class TestRemoteJobs(TestCase):

    base_dir = os.path.dirname(__file__)
    local_source_file = os.path.join(base_dir, 'files/solution.c')
    remote_source_file = '/test_worker_manager/' + _uuid() + 'add_solution.c'
    local_wrong_source_file = os.path.join(base_dir, 'files/wrong_solution.c')
    remote_wrong_source_file = (
        '/test_worker_manager/' + _uuid() + 'wrong_add_solution.c'
    )
    binary_file = '/test_worker_manager/' + _uuid() + 'add_solution'
    local_in_file = os.path.join(base_dir, 'files/in')
    remote_in_file = '/test_worker_manager/' + _uuid() + 'in'
    local_out_file = os.path.join(base_dir, 'files/out')
    remote_out_file = '/test_worker_manager/' + _uuid() + 'out'
    evaluation_recipe = [
        ('upload source', 'oioioi.evalmgr.tests.tests.upload_source'),
        ('compile source', 'oioioi.evalmgr.tests.tests.compile_source'),
        ('upload test', 'oioioi.evalmgr.tests.tests.upload_inout'),
        ('run', 'oioioi.evalmgr.tests.tests.run'),
    ]
    evaluation_env = dict(
        job_id=42,
        recipe=evaluation_recipe,
        local_source_file=local_source_file,
        remote_source_file=remote_source_file,
        binary_file=binary_file,
        local_in_file=local_in_file,
        remote_in_file=remote_in_file,
        local_out_file=local_out_file,
        remote_out_file=remote_out_file,
    )

    def tearDown(self):
        fc = get_client()
        for filename in (
            self.remote_source_file,
            self.remote_wrong_source_file,
            self.remote_in_file,
            self.remote_out_file,
        ):
            fc.delete_file(filename)

    @override_settings(
        SIOWORKERS_BACKEND='oioioi.evalmgr.tests.tests.SioworkersBackend'
    )
    def _run_with_dummy_sioworkers(self, testfn):
        testfn()

    def test_full_source_file_evaluation_with_dummy_sioworkers(self):
        self._run_with_dummy_sioworkers(self.test_full_source_file_evaluation)

    def test_multiple_source_file_evaluation_with_dummy_sioworkers(self):
        self._run_with_dummy_sioworkers(self.test_multiple_source_file_evaluation)

    def test_full_source_file_evaluation(self):
        env = self.evaluation_env.copy()
        env = delay_environ_wrapper(env).get()
        self.assertEqual('OK', env['result_code'])

    def test_multiple_source_file_evaluation(self):
        good_env = self.evaluation_env.copy()
        wrong_env = self.evaluation_env.copy()
        wrong_env.update(
            local_source_file=self.local_wrong_source_file,
            remote_source_file=self.remote_wrong_source_file,
        )
        good_result = delay_environ_wrapper(good_env)
        wrong_result = delay_environ_wrapper(wrong_env)
        self.assertEqual('OK', good_result.get()['result_code'])
        self.assertEqual('WA', wrong_result.get()['result_code'])


police_files = {}


class SuspectNotFoundException(Exception):
    pass


def police_handler(env, **kwargs):
    case = env['case']
    files = police_files.get(case, {})
    files['suspect_status'] = 'ARRESTED'
    police_files[case] = files
    return env


def corrupted_police_handler(env, **kwargs):
    raise SuspectNotFoundException


def set_mood(env, **kwargs):
    case = env['case']
    files = police_files.get(case, {})
    files['suspect_mood'] = kwargs.get('mood', 'ambivalent')
    police_files[case] = files
    return env


class TestErrorBehavior(TestCase):
    error_handlers = [
        ('Call police', 'oioioi.evalmgr.tests.tests.police_handler'),
        ('Be ashamed', 'oioioi.evalmgr.tests.tests.set_mood', {'mood': 'ashamed'}),
    ]

    arrest = [('Call police', 'oioioi.evalmgr.tests.tests.police_handler')]

    corrupted_error_handler = [
        ('Call police', 'oioioi.evalmgr.tests.tests.corrupted_police_handler')
    ]

    def test_error_behavior(self):
        case = 1
        tests = [  # evaluation error
            (
                dict(
                    recipe=hunting, area='elevator', error_handlers=self.error_handlers
                ),
                HuntingException,
                'ARRESTED',
                'ashamed',
            ),
            # job with no recipe
            (
                dict(
                    very_important_task='kill another hedgehog remotely',
                    error_handlers=self.arrest,
                ),
                RuntimeError,
                'ARRESTED',
                None,
            ),
            # handler not returning environment
            (
                dict(recipe=hunting, area='blackhole', error_handlers=self.arrest),
                RuntimeError,
                'ARRESTED',
                None,
            ),
            # corrupted error handler
            (
                dict(
                    recipe=hunting,
                    area='elevator',
                    error_handlers=self.corrupted_error_handler,
                ),
                HuntingException,
                None,
                None,
            ),
        ]

        for env, exception, status, mood in tests:
            police_files.clear()
            env['job_id'] = 42
            env['case'] = case
            with self.assertRaises(exception):
                delay_environ_wrapper(env).get()
            if status:
                self.assertEqual(status, police_files[case]['suspect_status'])
            if mood:
                self.assertEqual(mood, police_files[case]['suspect_mood'])


class TestAsyncJobs(TestCase):
    transferred_environs = []

    def _prepare(self):
        SavedEnviron.objects.all().delete()
        TestAsyncJobs.transferred_environs = []
        env = create_environ()
        env.setdefault('recipe', []).append(
            ('transfer', 'oioioi.evalmgr.tests.tests._call_transfer')
        )
        env['resumed'] = False
        return env

    def test_transfer_job(self):
        env = self._prepare()
        env = delay_environ_wrapper(env).get()
        res = TestAsyncJobs.transferred_environs.pop()
        self.assertIsNotNone(res)
        self.assertFalse(env['resumed'])
        self.assertIn('saved_environ_id', res)
        env = delay_environ_wrapper(res).get()
        self.assertTrue(env['resumed'])

    def test_environ_save(self):
        env = self._prepare()
        env = delay_environ_wrapper(env).get()
        res = TestAsyncJobs.transferred_environs.pop()
        self.assertEqual(SavedEnviron.objects.count(), 1)
        self.assertEqual(SavedEnviron.objects.get().id, res['saved_environ_id'])
        env = delay_environ_wrapper(res).get()
        self.assertTrue(env['resumed'])
        self.assertEqual(SavedEnviron.objects.count(), 0)

    def test_transfer_fail(self):
        env = self._prepare()
        env['transfer_successful'] = False
        with self.assertRaises(RuntimeError):
            env = delay_environ_wrapper(env).get()
        self.assertEqual(SavedEnviron.objects.count(), 0)

    def test_job_resumed_twice(self):
        env = self._prepare()
        env = delay_environ_wrapper(env).get()
        self.assertEqual(SavedEnviron.objects.count(), 1)
        res = TestAsyncJobs.transferred_environs.pop()
        env = delay_environ_wrapper(copy.deepcopy(res)).get()
        self.assertTrue(env['resumed'])
        self.assertEqual(SavedEnviron.objects.count(), 0)
        self.assertIn('saved_environ_id', res)
        self.assertIsNone(delay_environ_wrapper(res))
        self.assertEqual(SavedEnviron.objects.count(), 0)

    def test_saved_environ_id(self):
        env = self._prepare()
        ids = []
        for _ in range(2):
            delay_environ_wrapper(copy.deepcopy(env)).get()
            res = TestAsyncJobs.transferred_environs.pop()
            ids.append(res['saved_environ_id'])
            delay_environ_wrapper(res).get()
        self.assertNotEqual(ids[0], ids[1])


def _call_transfer(environ):
    environ['magic'] = 1234
    return transfer_job(
        environ,
        'oioioi.evalmgr.tests.tests._transfer',
        'oioioi.evalmgr.tests.tests._resume',
        transfer_kwargs={'transfer_magic': 42},
    )


def _resume(saved_environ, environ):
    assert saved_environ['job_id'] == environ['job_id']
    assert 'transfer' not in environ
    assert 'saved_environ_id' not in environ
    assert 'magic' not in environ
    assert saved_environ['magic'] == 1234
    environ['resumed'] = True
    return environ


def _transfer(environ, transfer_magic=None):
    assert 'transfer' not in environ
    assert 'saved_environ_id' in environ
    assert transfer_magic == 42

    saved_environ = QueuedJob.objects.get(job_id=environ['job_id']).savedenviron
    assert saved_environ.load_environ()['job_id'] == environ['job_id']

    if environ.get('transfer_successful', True):
        del environ['magic']
        TestAsyncJobs.transferred_environs.append(copy.deepcopy(environ))
    else:
        raise RuntimeError('Transfer failed')


class TestViews(TestCase):
    fixtures = [
        'test_users',
        'test_contest',
        'test_full_package',
        'test_problem_instance',
        'test_submission',
    ]

    def _get_admin_site(self):
        self.assertTrue(self.client.login(username='test_admin'))
        self.client.get('/c/c/')  # 'c' becomes the current contest
        show_response = self.client.get(
            reverse('oioioiadmin:evalmgr_queuedjob_changelist')
        )
        self.assertEqual(show_response.status_code, 200)
        return show_response

    def assertStateCountEqual(self, state_str, count, show_response=None):
        """Asserts that the number of the submits with given state
        (``state_str``) that appear on the admin site is ``count``.
        """
        if show_response is None:
            show_response = self._get_admin_site()

        self.assertContains(show_response, '>' + state_str + '</span>', count=count)

    def assertNotPresent(self, state_strs):
        """Asserts that none of the ``state_strs`` is present on the admin
        page
        """
        show_response = self._get_admin_site()
        for str in state_strs:
            self.assertStateCountEqual(str, 0, show_response)

    def test_admin_view(self):
        """Test if a submit shows on the list properly."""
        submission = Submission.objects.get(pk=1)
        qs = QueuedJob(submission=submission, state='QUEUED', celery_task_id='dummy')
        qs.save()
        self.assertStateCountEqual('Queued', 1)

        qs.state = 'PROGRESS'
        qs.save()

        self.assertStateCountEqual('In progress', 1)

        qs.state = 'CANCELLED'
        qs.save()

        self.assertNotPresent(['In progress', 'Queued'])


class AddHandlersController(ProgrammingContestController):
    pass


class TestEval(TestCase):
    fixtures = [
        'test_users',
        'test_contest',
        'test_full_package',
        'test_problem_instance',
        'test_submission',
    ]

    def test_add_handlers(self):
        """Test if the proper handlers are added to the recipe."""
        contest = Contest.objects.get()
        controller = AddHandlersController(contest)
        env = create_environ()
        env.setdefault('recipe', []).append(('dummy', 'dummy'))
        controller.finalize_evaluation_environment(env)

        self.assertIn(
            (
                'remove_queuedjob_on_error',
                'oioioi.evalmgr.handlers.remove_queuedjob_on_error',
            ),
            env['error_handlers'],
        )

    def test_revoke(self):
        """Test if a submit revokes properly."""
        job_id = 'dummy'
        env = {}
        env['job_id'] = job_id
        env['submission_id'] = 1
        env['celery_task_id'] = job_id

        submission = Submission.objects.get(pk=1)
        qs = QueuedJob(
            submission=submission,
            state='CANCELLED',
            celery_task_id=job_id,
            job_id=job_id,
        )
        qs.save()

        self.assertFalse(mark_job_state(env, state='PROGRESS'))
