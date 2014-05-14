# coding: utf-8
from datetime import datetime

from django.test import TestCase
from django.core.urlresolvers import reverse
from django.core.files.base import ContentFile
from django.utils.timezone import utc

from oioioi.testrun import handlers
from oioioi.testrun.models import TestRunProgramSubmission, TestRunReport
from oioioi.base.tests import check_not_accessible, check_ajax_not_accessible
from oioioi.contests.models import Contest, ProblemInstance, Submission
from oioioi.filetracker.client import get_client
from oioioi.filetracker.storage import FiletrackerStorage
from oioioi.base.tests import fake_time


class TestTestrunViews(TestCase):
    fixtures = ['test_users', 'test_contest', 'test_full_package',
            'test_testrun']

    def test_status_visible(self):
        self.client.login(username='test_user')
        submission = TestRunProgramSubmission.objects.get(pk=1)
        kwargs = {'contest_id': submission.problem_instance.contest.id,
                'submission_id': submission.id}

        with fake_time(datetime(2011, 8, 5, tzinfo=utc)):
            submission_view = self.client.get(reverse('submission',
                kwargs=kwargs))
            self.assertContains(submission_view, 'Input')
            self.assertContains(submission_view, 'Output')
            self.assertContains(submission_view, 'OK')
            submission_view = self.client.get(reverse('my_submissions',
                kwargs={'contest_id': submission.problem_instance.contest.id}))
            self.assertContains(submission_view, 'subm_OK">OK</td>')

    def test_input_views(self):
        self.client.login(username='test_user')
        submission = TestRunProgramSubmission.objects.get(pk=1)
        kwargs = {'contest_id': submission.problem_instance.contest.id,
                'submission_id': submission.id}

        with fake_time(datetime(2011, 8, 5, tzinfo=utc)):
            show_output = self.client.get(reverse('get_testrun_input',
                kwargs=kwargs), HTTP_X_REQUESTED_WITH='XMLHttpRequest')
            self.assertContains(show_output, '9 9')
            self.assertIn('Input', show_output.content)

            download_response = self.client.get(reverse(
                'download_testrun_input', kwargs=kwargs))

            self.assertContains(download_response, '9 9\n')
            self.assertTrue(download_response['Content-Disposition']
                            .startswith('attachment'))
            self.assertIn('filename="input.in"',
                download_response['Content-Disposition'])

    def test_output_views(self):
        self.client.login(username='test_user')
        submission = TestRunProgramSubmission.objects.get(pk=1)
        kwargs = {'contest_id': submission.problem_instance.contest.id,
                'submission_id': submission.id}

        with fake_time(datetime(2011, 8, 5, tzinfo=utc)):
            show_output = self.client.get(reverse('get_testrun_output',
                kwargs=kwargs), HTTP_X_REQUESTED_WITH='XMLHttpRequest')
            self.assertContains(show_output, '18')
            self.assertIn('Output', show_output.content)

            download_response = self.client.get(reverse(
                'download_testrun_output', kwargs=kwargs))

            self.assertContains(download_response, '18\n')
            self.assertTrue(download_response['Content-Disposition']
                            .startswith('attachment'))
            self.assertIn('filename="output.out"',
                          download_response['Content-Disposition'])

        with fake_time(datetime(2014, 8, 5, tzinfo=utc)):
            show_output = self.client.get(reverse('get_testrun_output',
                kwargs=kwargs), HTTP_X_REQUESTED_WITH='XMLHttpRequest')
            self.assertContains(show_output, '18')

    def test_submit_view(self):
        self.client.login(username='test_user')
        kwargs = {'contest_id': Contest.objects.get().id}
        url = reverse('testrun_submit', kwargs=kwargs)

        response = self.client.get(url)
        self.assertContains(response, 'Input')
        self.assertContains(response, 'name="input"')
        self.assertContains(response, u'Sumżyce')

        data = {
            'problem_instance_id': ProblemInstance.objects.get().id,
            'file': ContentFile('a', name='x.cpp'),
            'input': ContentFile('i', name='x.cpp'),
        }
        response = self.client.post(url, data, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Submission.objects.filter(kind='TESTRUN').count(), 2)
        submission = TestRunProgramSubmission.objects.get(pk=2)
        self.assertEqual(submission.kind, 'TESTRUN')
        self.assertEqual(submission.input_file.read().strip(), 'i')
        self.assertEqual(submission.source_file.read().strip(), 'a')

        self.client.login(username='test_admin')
        response = self.client.get(url)
        self.assertContains(response, 'TESTRUN')
        self.assertNotIn('NORMAL', response.content)

    def test_code_pasting(self):
        self.client.login(username='test_user')
        kwargs = {'contest_id': Contest.objects.get().id}
        url = reverse('testrun_submit', kwargs=kwargs)
        data = {
            'problem_instance_id': ProblemInstance.objects.get().id,
            'code': 'some code',
            'prog_lang': 'C',
            'input': ContentFile('i', name='x.cpp'),
        }
        response = self.client.post(url, data, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Submission.objects.filter(kind='TESTRUN').count(), 2)
        submission = TestRunProgramSubmission.objects.get(pk=2)
        self.assertEqual(submission.kind, 'TESTRUN')
        self.assertEqual(submission.input_file.read().strip(), 'i')
        self.assertEqual(submission.source_file.read().strip(), 'some code')

    def test_submissions_permissions(self):
        submission = TestRunProgramSubmission.objects.get(pk=1)
        kwargs = {'contest_id': submission.problem_instance.contest.id,
                'submission_id': submission.id}

        self.client.login(username='test_user2')
        for view in ['get_testrun_output', 'get_testrun_input',
                        'download_testrun_output', 'download_testrun_input']:
            check_not_accessible(self, view, kwargs=kwargs)

        for view in ['get_testrun_output', 'get_testrun_input']:
            check_ajax_not_accessible(self, view, kwargs=kwargs)

        contest = Contest.objects.get(pk='c')
        contest.controller_name = \
                'oioioi.contests.tests.PrivateContestController'
        contest.save()
        self.client.logout()
        for view in ['get_testrun_output', 'get_testrun_input']:
            check_ajax_not_accessible(self, view, kwargs=kwargs)


class TestWithNoTestruns(TestCase):
    fixtures = ['test_users', 'test_contest', 'test_full_package']

    def test_not_visible(self):
        self.client.login(username='test_user')
        kwargs = {'contest_id': Contest.objects.get().id}
        url = reverse('testrun_submit', kwargs=kwargs)
        response = self.client.get(url)
        self.assertIn("for which you could run", response.content)


class TestHandlers(TestCase):
    fixtures = ['test_users', 'test_contest', 'test_full_package',
            'test_testrun']

    def test_handlers(self):
        submission = TestRunProgramSubmission.objects.get(pk=1)

        environ = {}
        environ['job_id'] = 'job_id'
        environ['submission_id'] = submission.id
        environ['submission_kind'] = submission.kind
        environ['problem_instance_id'] = submission.problem_instance.id
        environ['problem_id'] = submission.problem.id
        environ['round_id'] = submission.problem_instance.round.id
        environ['contest_id'] = submission.problem_instance.id

        # Simulate successful compilation
        environ['compilation_result'] = 'OK'
        environ['compilation_message'] = ''

        environ = handlers.make_test(environ)

        self.assertIn('tests', environ)
        self.assertIn('test', environ['tests'])
        self.assertIn('in_file', environ['tests']['test'])

        # Simulate running tests
        FiletrackerStorage().save('output', ContentFile('o'))
        try:
            environ['test_results'] = {}
            environ['test_results']['test'] = {
                'result_cpode': 'OK',
                'result_string': 'OK',
                'time_used': 111,
                'out_file': '/output'
            }

            environ = handlers.grade_submission(environ)

            self.assertEqual(None, environ['score'])
            self.assertEqual('OK', environ['status'])

            environ = handlers.make_report(environ)
            self.assertIn('report_id', environ)
            report = TestRunReport.objects.get(
                                    submission_report=environ['report_id'])
            self.assertEqual(111, report.time_used)
            self.assertEqual('', report.comment)
            self.assertEqual('o', report.output_file.read())

            handlers.delete_output(environ)
        except StandardError:
            get_client().delete_file('/output')
