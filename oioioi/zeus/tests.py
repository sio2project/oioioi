import json
import urllib

from django.test import TestCase
from django.test.utils import override_settings
from django.core.urlresolvers import reverse

from oioioi.base.tests import TestsUtilsMixin
from oioioi.contests.models import Contest, ProblemInstance, SubmissionReport
from oioioi.problems.models import Problem
from oioioi.programs.models import ProgramSubmission
from oioioi.sinolpack.tests import get_test_filename
from oioioi.zeus.backends import _json_base64_encode, _json_base64_decode, \
                                 Base64String, ZeusServer
from oioioi.zeus.models import ZeusAsyncJob, ZeusTestRunProgramSubmission, \
                               ZeusProblemData
from oioioi.zeus.management.commands import zeus_fetcher
# Import qualified to prevent nose from thinking that
# '(^|_)test*' functions are tests
from oioioi.zeus import handlers


def ZeusTestServer(fixtures_path):
    """Parametrized class for test zeus server, returning results from
       fixtures.
    """
    class _ZeusTestServer(ZeusServer):
        def __init__(self, zeus_id, server):
            super(_ZeusTestServer, self).__init__(zeus_id, server)
            with open(fixtures_path) as f:
                self.fixtures = json.load(f)

        def _send(self, url, data=None, method='GET', **kwargs):
            assert data is None or method == 'POST'
            matching_fixtures = [f for f in self.fixtures if f['url'] == url
                                 and f['method'] == method]
            assert len(matching_fixtures) == 1
            fix = matching_fixtures[0]
            return fix['result_code'], fix['result']
    return _ZeusTestServer


ZeusCorrectServer = ZeusTestServer(
        'oioioi/zeus/fixtures/test_zeus_correct.json')
ZeusIncorrectServer = ZeusTestServer(
        'oioioi/zeus/fixtures/test_zeus_incorrect.json')


class ZeusDummyServer(ZeusServer):
    # pylint: disable=super-init-not-called
    def __init__(self, zeus_id, server_info):
        pass

    def send_regular(self, zeus_problem_id, kind, source_file, language):
        return 1917141 if kind == 'INITIAL' else 909941

    def send_testrun(self, zeus_problem_id, source_file, language, input_file,
            library_file):
        return 73579009

    def fetch_results(self):
        return 0, []

    def commit_fetch(self, seq):
        pass

    def download_output(self, output_id):
        return 'a' * 1234


def _updated_copy(dict1, dict2):
    new_dict = dict1.copy()
    new_dict.update(dict2)
    return new_dict


class ZeusJsonTest(TestCase):
    def setUp(self):
        self._ob = {
            u'dict': {u'key': Base64String('somestring')},
            u'key': Base64String('string'),
        }
        self._ob_json = \
                '{"dict": {"key": "c29tZXN0cmluZw=="}, "key": "c3RyaW5n"}'

        with open('oioioi/zeus/fixtures/test_zeus_correct.json') as f:
            self._jsons = [f['result'] for f in json.load(f)]

        self._json_base64_decode = lambda v: _json_base64_decode(v, wrap=True)

    def test_json_base64_encode(self):
        self.assertEquals(_json_base64_encode(self._ob), self._ob_json)

    def test_json_base64_decode(self):
        self.assertEquals(self._ob, self._json_base64_decode(self._ob_json))
        for j in self._jsons:
            self._json_base64_decode(j)

    def test_json_base64_identity(self):
        self.assertEquals(self._ob, self._json_base64_decode(
                          _json_base64_encode(self._ob)))
        self.assertEquals(self._ob_json, _json_base64_encode(
                          self._json_base64_decode(self._ob_json)))
        for j in self._jsons:
            self.assertEquals(j, _json_base64_encode(
                    self._json_base64_decode(j)))


class ZeusHandlersTest(TestsUtilsMixin, TestCase):
    fixtures = ['test_users', 'test_contest', 'test_full_package',
            'test_problem_instance', 'test_submission', 'test_zeus_problem']

    def _verify_metadata_decoder(self, data):
        self.assertAllIn(['name', 'group', 'max_score'], data)

    def test_testrun_metadata(self):
        data = handlers.testrun_metadata('')
        self.assertEqual(data['name'], 'test')
        self.assertEqual(data['max_score'], 0)
        self._verify_metadata_decoder(data)

    def test_csv_metadata_decoder(self):
        def check_str(metadata, name, group, score):
            data = handlers.from_csv_metadata(metadata)
            self._verify_metadata_decoder(data)
            self.assertEquals(data,
                    {'name': name, 'group': group, 'max_score': score})

        check_str('1b,1,99', '1b', '1', 99)
        check_str('test32d  ,  ,  123', 'test32d', 'test32d', 123)

    def test_submit_job(self):
        env = {
            'submission_id': 1,
            'language': 'cpp',
            'zeus_id': 'dummy',
            'zeus_problem_id': 1
        }
        env = handlers.submit_job(env, kind='INITIAL')
        self.assertEqual(env['zeus_check_uids']['INITIAL'], 1917141)
        env = handlers.submit_job(env, kind='NORMAL')
        self.assertEqual(env['zeus_check_uids']['INITIAL'], 1917141)
        self.assertEqual(env['zeus_check_uids']['NORMAL'], 909941)

    def test_submit_testrun_job(self):
        env = {
            'submission_id': 1,
            'language': 'cpp',
            'zeus_id': 'dummy',
            'zeus_problem_id': 1
        }
        ps = ProgramSubmission.objects.get()
        ztrps = ZeusTestRunProgramSubmission(programsubmission_ptr=ps)
        ztrps.input_file = None
        ztrps.library_file = None
        ztrps.__dict__.update(ps.__dict__)  # A hack to extend existing model
        ztrps.save()

        env = handlers.submit_testrun_job(env)
        self.assertEqual(env['zeus_check_uids']['TESTRUN'], 73579009)

    def test_save_env(self):
        env = {
            'recipe': (('1kg_of_flour', 'take.and.put.it.in.a.bowl'),),
            'zeus_check_uids': {'NORMAL': 909941, 'X': 1337},
            'eggs_available': True,
        }
        env = handlers.save_env(env, kind='NORMAL')
        self.assertEquals(len(env['recipe']), 0)
        job = ZeusAsyncJob.objects.get(check_uid=909941)
        saved_env = json.loads(job.environ)
        self.assertTrue(saved_env['eggs_available'])
        self.assertEquals(len(saved_env['recipe']), 1)

    def _get_base_report(self, check_uid, kind, metadata=''):
        return {
            'check_uid': check_uid,
            'compilation_successful': True,
            'compilation_message': '',
            'report_kind': kind,
            'status': 'OK',
            'result_string': '',
            'metadata': metadata,
            'execution_time_ms': 100,
            'time_limit_ms': 1000,
            'memory_limit_byte': 2 ** 24,
        }

    def test_compilation_failure(self):
        report = _updated_copy(
                self._get_base_report(1917141, 'INITIAL'),
                {'compilation_successful': False, 'compilation_message': 'xx'})

        results = [
            _updated_copy(report, {'metadata': '0a,0,0'}),
            _updated_copy(report, {'metadata': '0b,0,0'})
        ]
        env = {'zeus_results': results}
        env = handlers.import_results(env, kind='INITIAL')
        self.assertEqual(env['compilation_result'], 'CE')
        self.assertEqual(env['compilation_message'], 'xx')
        self.assertNotIn('tests', env)
        self.assertNotIn('test_results', env)

    def test_importing(self):
        report = self._get_base_report(909941, 'NORMAL')
        other_report = self._get_base_report(9999, 'XXXX')
        report_2 = _updated_copy(report, {'metadata': '2,2,55'})
        results = [
            _updated_copy(report, {'metadata': '1a,1,2'}),
            _updated_copy(report, {'metadata': '1b,1,2', 'status': 'WA',
                'result_string': 'wa'}),
            report_2,
            other_report,
        ]
        env = {'zeus_results': results}
        env = handlers.import_results(env, kind='NORMAL')
        self.assertEqual(env['compilation_result'], 'OK')
        self.assertEqual(env['compilation_message'], '')

        tests = env['tests']
        test_results = env['test_results']
        self.assertEqual(len(tests), 3)
        self.assertEqual(len(test_results), 3)
        self.assertAllIn(['1a', '1b', '2'], tests)

        self.assertDictContainsSubset({'name': '1a', 'kind': 'NORMAL',
                    'group': '1', 'max_score': 2, 'exec_time_limit': 1000,
                    'exec_memory_limit': 2 ** 14, 'zeus_metadata': '1a,1,2'},
                tests['1a'])
        self.assertDictContainsSubset({'result_code': 'WA',
                'result_string': 'wa', 'time_used': 100}, test_results['1b'])
        self.assertDictEqual(report_2, test_results['2']['zeus_test_result'])

        env['zeus_results'].append(
                self._get_base_report(1917141, 'INITIAL', '0,0,0'))
        env = handlers.import_results(env, kind='INITIAL', map_to_kind='EGGY')
        self.assertEqual(len(tests), 4)
        self.assertEqual(len(test_results), 4)
        self.assertDictContainsSubset({'name': '0', 'kind': 'EGGY'},
                env['tests']['0'])

    def test_make_zeus_testrun_report(self):
        report = _updated_copy(self._get_base_report(73579009, 'TESTRUN', ''),
                {'stdout_size': 1024, 'stdout': 'some out', 'stdout_uid': 918})
        env = {
            'zeus_results': [report],
            'score': None,
            'max_score': None,
            'status': 'OK',
            'zeus_metadata_decoder': 'oioioi.zeus.handlers.testrun_metadata',
            'submission_id': 1,
        }
        env = handlers.import_results(env, kind='TESTRUN')
        self.assertEqual(len(env['tests']), 1)
        self.assertEqual(len(env['test_results']), 1)
        env = handlers.make_zeus_testrun_report(env)
        submission_report = SubmissionReport.objects.get(id=env['report_id'])
        self.assertEqual(submission_report.kind, 'TESTRUN')
        tr_report = submission_report.testrunreport_set.get().zeustestrunreport
        self.assertEqual(tr_report.status, 'OK')
        self.assertEqual(tr_report.time_used, 100)
        self.assertEqual(tr_report.test_time_limit, 1000)
        self.assertEqual(tr_report.output_file.read(), 'some out')

        self.assertEqual(tr_report.full_out_size, 1024)
        self.assertEqual(tr_report.full_out_handle, '918')


@override_settings(ZEUS_INSTANCES={'zeus_correct': ('__use_object__',
                                   'oioioi.zeus.tests.ZeusCorrectServer',
                                   ('zeus_fixture_server/', '', ''))})
class TestZeusFetcher(TestCase):
    fixtures = ['test_users', 'test_contest', 'test_full_package',
            'test_problem_instance', 'test_submission', 'test_zeus_problem']

    def setUp(self):
        self.fetcher = zeus_fetcher.Command()

    def test_fetch_once(self):
        env = {'recipe': []}
        ZeusAsyncJob.objects.create(check_uid='1001', environ=json.dumps(env))
        self.fetcher.fetch_once(self.fetcher.zeus_servers.values()[0])
        self.assertEquals(ZeusAsyncJob.objects.all().count(), 2)
        z1 = ZeusAsyncJob.objects.get(check_uid='1001')
        z2 = ZeusAsyncJob.objects.get(check_uid='1003')
        self.assertTrue(z1.resumed)
        self.assertFalse(z2.resumed)


class TestZeusProblemUpload(TestCase):
    fixtures = ['test_users', 'test_contest']

    def test_upload_package(self):
        ProblemInstance.objects.all().delete()

        contest = Contest.objects.get()
        filename = get_test_filename('test_simple_package.zip')
        self.client.login(username='test_admin')
        url = reverse('oioioi.problems.views.add_or_update_problem_view',
                kwargs={'contest_id': contest.id}) + '?' + \
                        urllib.urlencode({'key': 'zeus'})
        data = {
            'package_file': open(filename, 'rb'),
            'zeus_id': 'dummy',
            'zeus_problem_id': 1,
        }
        response = self.client.post(url, data, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Problem.objects.count(), 1)
        self.assertEqual(ProblemInstance.objects.count(), 2)
        self.assertEqual(ZeusProblemData.objects.count(), 1)
