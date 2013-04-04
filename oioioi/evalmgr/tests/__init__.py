from django.utils import unittest
from django.test.utils import override_settings
from django.test import SimpleTestCase
from oioioi.evalmgr import evalmgr_job
from oioioi.sioworkers.jobs import run_sioworkers_job
from oioioi.filetracker.client import get_client

import copy
import uuid
import os.path

hunting = [ ('Prepare guns',
                'oioioi.evalmgr.tests.prepare_handler'),
            ('Hunt',
                'oioioi.evalmgr.tests.hunting_handler',
                {'animal': 'hedgehog'}),
            ('Rest',
                'oioioi.evalmgr.tests.rest_handler') ]

class HuntingException(Exception):
    pass

def hunting_handler(env, **kwargs):
    if kwargs['animal'] == 'hedgehog' and env['area'] == 'forest' \
            and env['prepared'] == True:
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

class TestLocalJobs(unittest.TestCase):
    def test_evalmgr_job(self):
        env = dict(recipe=hunting, area='forest')
        env = evalmgr_job.delay(env).get()
        self.assertEqual('Hedgehog hunted.', env['output'])

    def test_cascade_job(self):
        env = dict(recipe=hunting, area='forest')
        env = evalmgr_job.delay(env).get()
        self.assertEqual('Hedgehog hunted.', env['output'])

    def test_multiple_jobs(self):
        city_result = evalmgr_job.delay(dict(recipe=hunting, area='city'))
        forest_result = evalmgr_job.delay(dict(recipe=hunting, area='forest'))
        jungle_result = evalmgr_job.delay(dict(recipe=hunting, area='jungle'))
        self.assertEqual('Hedgehog hunted.', forest_result.get()['output'])
        self.assertEqual('Epic fail.', city_result.get()['output'])
        self.assertEqual('Epic fail.', jungle_result.get()['output'])

def upload_source(env, **kwargs):
    fc = get_client()
    fc.put_file(env['remote_source_file'], env['local_source_file'])
    return env

def compile_source(env, **kwargs):
    env.update(dict(
        source_file=env['remote_source_file'],
        out_file=env['binary_file'],
        compiler='system-gcc',
        job_type='compile'))
    return run_sioworkers_job(env)

def upload_inout(env, **kwargs):
    fc = get_client()
    env.update({
        'in_file': env['remote_in_file'],
        'hint_file': env['remote_out_file']})
    fc.put_file(env['remote_in_file'], env['local_in_file'])
    fc.put_file(env['remote_out_file'], env['local_out_file'])
    return env

def run(env, **kwargs):
    env.update(dict(
        exe_file=env['binary_file'],
        check_output=True,
        job_type='unsafe-exec'))
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

class TestRemoteJobs(SimpleTestCase):
    def uuid():
        return uuid.uuid4().hex

    base_dir = os.path.dirname(__file__)
    local_source_file = os.path.join(base_dir, 'files/solution.c')
    remote_source_file = '/test_worker_manager/' + uuid() + 'add_solution.c'
    local_wrong_source_file = os.path.join(base_dir, 'files/wrong_solution.c')
    remote_wrong_source_file = '/test_worker_manager/' + uuid() + \
            'wrong_add_solution.c'
    binary_file = '/test_worker_manager/' + uuid() + 'add_solution'
    local_in_file = os.path.join(base_dir, 'files/in')
    remote_in_file = '/test_worker_manager/' + uuid() + 'in'
    local_out_file = os.path.join(base_dir, 'files/out')
    remote_out_file = '/test_worker_manager/' + uuid() + 'out'
    evaluation_recipe = [
        ('upload source',
        'oioioi.evalmgr.tests.upload_source'),
        ('compile source',
        'oioioi.evalmgr.tests.compile_source'),
        ('upload test',
        'oioioi.evalmgr.tests.upload_inout'),
        ('run',
        'oioioi.evalmgr.tests.run'),
    ]
    evaluation_env = dict(
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
        for filename in (self.remote_source_file,
                self.remote_wrong_source_file, self.remote_in_file,
                self.remote_out_file):
            fc.delete_file(filename)

    @override_settings(
            SIOWORKERS_BACKEND='oioioi.evalmgr.tests.SioworkersBackend')
    def _run_with_dummy_sioworkers(self, testfn):
        testfn()

    def test_full_source_file_evaluation_with_dummy_sioworkers(self):
        self._run_with_dummy_sioworkers(self.test_full_source_file_evaluation)

    def test_multiple_source_file_evaluation_with_dummy_sioworkers(self):
        self._run_with_dummy_sioworkers(self.test_multiple_source_file_evaluation)

    def test_full_source_file_evaluation(self):
        env = self.evaluation_env.copy()
        env = evalmgr_job.delay(env).get()
        self.assertEqual('OK', env['result_code'])

    def test_multiple_source_file_evaluation(self):
        good_env = self.evaluation_env.copy()
        wrong_env = self.evaluation_env.copy()
        wrong_env.update(
            local_source_file=self.local_wrong_source_file,
            remote_source_file=self.remote_wrong_source_file
            )
        good_result = evalmgr_job.delay(good_env)
        wrong_result = evalmgr_job.delay(wrong_env)
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

class TestErrorBehavior(unittest.TestCase):
    error_handlers = [
            ('Call police',
                'oioioi.evalmgr.tests.police_handler'),
            ('Be ashamed',
                'oioioi.evalmgr.tests.set_mood',
                {'mood': 'ashamed'}) ]

    arrest = [
            ('Call police',
                'oioioi.evalmgr.tests.police_handler')]

    corrupted_error_handler = [
        ('Call police',
         'oioioi.evalmgr.tests.corrupted_police_handler') ]

    def test_error_behavior(self):
        case = 1
        tests = [ # evaluation error
                  (dict(recipe=hunting, area='elevator',
                        error_handlers=self.error_handlers),
                   HuntingException, 'ARRESTED', 'ashamed'),

                  # job with no recipe
                  (dict(very_important_task='kill another hedgehog remotely',
                        error_handlers=self.arrest),
                   RuntimeError, 'ARRESTED', None),

                  # handler not returning environment
                  (dict(recipe=hunting, area='blackhole',
                        error_handlers=self.arrest),
                   RuntimeError, 'ARRESTED', None),

                  # corrupted error handler
                  (dict(recipe=hunting, area='elevator',
                        error_handlers=self.corrupted_error_handler),
                   HuntingException, None, None) ]

        for env, exception, status, mood in tests:
            police_files.clear()
            env['case'] = case
            with self.assertRaises(exception):
                evalmgr_job.delay(env).get()
            if status:
                self.assertEqual(status, police_files[case]['suspect_status'])
            if mood:
                self.assertEqual(mood, police_files[case]['suspect_mood'])
