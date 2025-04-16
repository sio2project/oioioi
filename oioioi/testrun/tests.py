# coding: utf-8
import os
import re
from datetime import datetime, timezone  # pylint: disable=E0611

from django.contrib.auth.models import User
from django.core.files.base import ContentFile
from django.urls import reverse

from oioioi.base.tests import (
    TestCase,
    check_ajax_not_accessible,
    check_not_accessible,
    fake_time,
)
from oioioi.base.utils.archive import Archive
from oioioi.contests.models import Contest, ProblemInstance, Submission
from oioioi.evalmgr.tasks import create_environ
from oioioi.filetracker.client import get_client
from oioioi.filetracker.storage import FiletrackerStorage
from oioioi.programs.tests import SubmitFileMixin
from oioioi.programs.utils import form_field_id_for_langs
from oioioi.testrun import handlers
from oioioi.testrun.models import TestRunConfig, TestRunProgramSubmission, TestRunReport


class TestTestrunViews(TestCase):
    fixtures = [
        'test_users',
        'test_contest',
        'test_full_package',
        'test_problem_instance',
        'test_testrun',
    ]

    def test_status_visible(self):
        self.assertTrue(self.client.login(username='test_user'))
        submission = TestRunProgramSubmission.objects.get(pk=1)
        kwargs = {
            'contest_id': submission.problem_instance.contest.id,
            'submission_id': submission.id,
        }

        with fake_time(datetime(2011, 8, 5, tzinfo=timezone.utc)):
            submission_view = self.client.get(reverse('submission', kwargs=kwargs))
            self.assertContains(submission_view, 'Input')
            self.assertContains(submission_view, 'Output')
            self.assertContains(submission_view, 'OK')
            submission_view = self.client.get(
                reverse(
                    'my_submissions',
                    kwargs={'contest_id': submission.problem_instance.contest.id},
                )
            )
            self.assertContains(submission_view, 'submission--OK"')

            no_whitespaces = re.sub(r'\s*', '', submission_view.content.decode('utf-8'))
            self.assertIn('>OK</td>', no_whitespaces)

    def test_input_views(self):
        self.assertTrue(self.client.login(username='test_user'))
        submission = TestRunProgramSubmission.objects.get(pk=1)
        kwargs = {
            'contest_id': submission.problem_instance.contest.id,
            'submission_id': submission.id,
        }

        with fake_time(datetime(2011, 8, 5, tzinfo=timezone.utc)):
            show_output = self.client.get(
                reverse('get_testrun_input', kwargs=kwargs),
                headers={"x-requested-with": 'XMLHttpRequest'}
            )
            self.assertContains(show_output, '9 9')
            self.assertContains(show_output, 'Input')

            download_response = self.client.get(
                reverse('download_testrun_input', kwargs=kwargs)
            )

            self.assertContains(download_response, '9 9\n')
            self.assertTrue(
                download_response['Content-Disposition'].startswith('attachment')
            )
            self.assertIn(
                'filename="input.in"', download_response['Content-Disposition']
            )

    def test_output_views(self):
        self.assertTrue(self.client.login(username='test_user'))
        submission = TestRunProgramSubmission.objects.get(pk=1)
        kwargs = {
            'contest_id': submission.problem_instance.contest.id,
            'submission_id': submission.id,
        }

        with fake_time(datetime(2011, 8, 5, tzinfo=timezone.utc)):
            show_output = self.client.get(
                reverse('get_testrun_output', kwargs=kwargs),
                headers={"x-requested-with": 'XMLHttpRequest'}
            )
            self.assertContains(show_output, '18')
            self.assertContains(show_output, 'Output')

            download_response = self.client.get(
                reverse('download_testrun_output', kwargs=kwargs)
            )

            self.assertContains(download_response, '18\n')
            self.assertTrue(
                download_response['Content-Disposition'].startswith('attachment')
            )
            self.assertIn(
                'filename="output.out"', download_response['Content-Disposition']
            )

        with fake_time(datetime(2014, 8, 5, tzinfo=timezone.utc)):
            show_output = self.client.get(
                reverse('get_testrun_output', kwargs=kwargs),
                headers={"x-requested-with": 'XMLHttpRequest'}
            )
            self.assertContains(show_output, '18')

    def test_submit_view(self):
        self.assertTrue(self.client.login(username='test_user'))
        kwargs = {'contest_id': Contest.objects.get().id}
        url = reverse('testrun_submit', kwargs=kwargs)

        response = self.client.get(url)
        self.assertContains(response, 'Input')
        self.assertContains(response, 'name="input"')
        self.assertContains(response, u'Sumżyce')
        data = {
            'problem_instance_id': ProblemInstance.objects.get().id,
            'file': ContentFile(b'a', name='x.cpp'),
            'input': ContentFile(b'i', name='x.cpp'),
        }
        response = self.client.post(url, data, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Submission.objects.filter(kind='TESTRUN').count(), 2)
        submission = TestRunProgramSubmission.objects.latest('pk')
        self.assertEqual(submission.kind, 'TESTRUN')
        self.assertEqual(submission.input_file.read().strip(), b'i')
        self.assertEqual(submission.source_file.read().strip(), b'a')

        self.assertTrue(self.client.login(username='test_admin'))
        response = self.client.get(url)
        self.assertContains(response, 'TESTRUN')
        self.assertNotContains(response, 'NORMAL')

    def test_archive_submission(self):
        self.assertTrue(self.client.login(username='test_user'))
        kwargs = {'contest_id': Contest.objects.get().id}
        url = reverse('testrun_submit', kwargs=kwargs)

        base_dir = os.path.join(os.path.dirname(__file__), 'files')

        testruns_before = Submission.objects.filter(kind='TESTRUN').count()
        for bad_archive in ['over_limit.zip', 'two_files.zip', 'evil.zip']:
            filename = os.path.join(base_dir, bad_archive)
            with open(filename, 'rb') as input_file:
                data = {
                    'problem_instance_id': ProblemInstance.objects.get().id,
                    'file': ContentFile(b'a', name='x.cpp'),
                    'input': input_file,
                }
                response = self.client.post(url, data, follow=True)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(
                    Submission.objects.filter(kind='TESTRUN').count(), testruns_before
                )

        with open(os.path.join(base_dir, "single_file.zip"), 'rb') as input_file:
            data = {
                'problem_instance_id': ProblemInstance.objects.get().id,
                'file': ContentFile(b'a', name='x.cpp'),
                'input': input_file,
            }
            response = self.client.post(url, data, follow=True)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(
                Submission.objects.filter(kind='TESTRUN').count(), testruns_before + 1
            )
            submission = TestRunProgramSubmission.objects.latest('pk')
            self.assertEqual(submission.kind, 'TESTRUN')
            self.assertEqual(submission.source_file.read().strip(), b'a')
            archive = Archive(submission.input_file, '.zip')
            self.assertEqual(len(archive.filenames()), 1)

    def test_code_pasting(self):
        self.assertTrue(self.client.login(username='test_user'))
        kwargs = {'contest_id': Contest.objects.get().id}
        url = reverse('testrun_submit', kwargs=kwargs)
        pi = ProblemInstance.objects.get()
        langs_field_name = form_field_id_for_langs(pi)
        data = {
            'problem_instance_id': pi.id,
            'code': 'some code',
            langs_field_name: 'C',
            'input': ContentFile(b'i', name='x.cpp'),
        }
        response = self.client.post(url, data, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Submission.objects.filter(kind='TESTRUN').count(), 2)
        submission = TestRunProgramSubmission.objects.latest('pk')
        self.assertEqual(submission.kind, 'TESTRUN')
        self.assertEqual(submission.input_file.read().strip(), b'i')
        self.assertEqual(submission.source_file.read().strip(), b'some code')

    def test_submissions_permissions(self):
        submission = TestRunProgramSubmission.objects.get(pk=1)
        kwargs = {
            'contest_id': submission.problem_instance.contest.id,
            'submission_id': submission.id,
        }

        self.assertTrue(self.client.login(username='test_user2'))
        for view in [
            'get_testrun_output',
            'get_testrun_input',
            'download_testrun_output',
            'download_testrun_input',
        ]:
            check_not_accessible(self, view, kwargs=kwargs)

        for view in ['get_testrun_output', 'get_testrun_input']:
            check_ajax_not_accessible(self, view, kwargs=kwargs)

        contest = Contest.objects.get(pk='c')
        contest.controller_name = 'oioioi.contests.tests.PrivateContestController'
        contest.save()
        self.client.logout()
        for view in ['get_testrun_output', 'get_testrun_input']:
            check_ajax_not_accessible(self, view, kwargs=kwargs)


class TestWithNoTestruns(TestCase):
    fixtures = [
        'test_users',
        'test_contest',
        'test_full_package',
        'test_problem_instance',
    ]

    def test_not_visible(self):
        self.assertTrue(self.client.login(username='test_user'))
        kwargs = {'contest_id': Contest.objects.get().id}
        url = reverse('testrun_submit', kwargs=kwargs)
        response = self.client.get(url)
        self.assertContains(response, "for which you could run")


class TestHandlers(TestCase):
    fixtures = [
        'test_users',
        'test_contest',
        'test_full_package',
        'test_problem_instance',
        'test_testrun',
    ]

    def test_handlers(self):
        submission = TestRunProgramSubmission.objects.get(pk=1)

        environ = create_environ()
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
        FiletrackerStorage().save('output', ContentFile(b'o'))
        try:
            environ['test_results'] = {}
            environ['test_results']['test'] = {
                'result_cpode': 'OK',
                'result_string': 'OK',
                'time_used': 111,
                'out_file': '/output',
            }

            environ = handlers.grade_submission(environ)

            self.assertEqual(None, environ['score'])
            self.assertEqual('OK', environ['status'])

            environ = handlers.make_report(environ)
            self.assertIn('report_id', environ)
            report = TestRunReport.objects.get(submission_report=environ['report_id'])
            self.assertEqual(111, report.time_used)
            self.assertEqual('', report.comment)
            self.assertEqual('o', report.output_file.read())

            handlers.delete_output(environ)
        except Exception:
            get_client().delete_file('/output')


class TestRunTestCase(object):
    """A TestCase mixin that provides some helpers for test run tests."""

    __test__ = False

    def submit_test_run(
        self,
        user,
        contest,
        problem_instance,
        source_name='submission.cpp',
        source_contents=b'<test run source>',
        input_name='input.txt',
        input_contents=b'<test run input>',
    ):
        url = reverse('testrun_submit', kwargs={'contest_id': contest.id})

        source_file = ContentFile(source_contents, name=source_name)
        input_file = ContentFile(input_contents, name=input_name)

        post_data = {
            'problem_instance_id': problem_instance.id,
            'file': source_file,
            'input': input_file,
            'kind': 'TESTRUN',
            'user': user,
        }

        return self.client.post(url, post_data, follow=True)


class TestTestRunsLimit(TestCase, TestRunTestCase, SubmitFileMixin):
    __test__ = True

    fixtures = [
        'test_users',
        'test_contest',
        'test_full_package',
        'test_problem_instance',
    ]

    def setUp(self):
        self.user = User.objects.get(username='test_user')
        self.contest = Contest.objects.get(pk='c')
        self.problem_instance = ProblemInstance.objects.get(pk=1)

        self.assertTrue(self.client.login(username=self.user.username))

        # Enable test runs for problem
        self.test_run_config = TestRunConfig(
            problem_instance=self.problem_instance,
            time_limit=10000,
            memory_limit=128 * 1024,
        )
        self.test_run_config.save()

    def submit_solution(self, is_testrun):
        if is_testrun:
            return self.submit_test_run(self.user, self.contest, self.problem_instance)
        else:
            return self.submit_file(self.contest, self.problem_instance, user=self.user)

    def test_test_run_limit_should_be_respected(self):
        self.test_run_config.test_runs_limit = 1
        self.test_run_config.save()

        first_test_run_response = self.submit_solution(is_testrun=True)
        second_test_run_response = self.submit_solution(is_testrun=True)

        self.assertNotRegex(
            first_test_run_response.content.decode('utf-8'), 'limit.*exceeded'
        )
        self.assertRegex(
            second_test_run_response.content.decode('utf-8'), 'limit.*exceeded'
        )

    def test_test_run_limit_should_be_independent_from_submission_limit(self):
        self.problem_instance.submissions_limit = 1000
        self.problem_instance.save()

        self.test_run_config.test_runs_limit = 1
        self.test_run_config.save()

        self.submit_solution(is_testrun=True)
        second_test_run_response = self.submit_solution(is_testrun=True)

        self.submit_solution(is_testrun=False)
        second_normal_response = self.submit_solution(is_testrun=False)

        self.assertRegex(
            second_test_run_response.content.decode('utf-8'), 'limit.*exceeded'
        )
        self.assertNotRegex(
            second_normal_response.content.decode('utf-8'), 'limit.*exceeded'
        )

    def test_zero_test_run_limit_should_mean_unlimited_test_runs(self):
        self.test_run_config.test_runs_limit = 0
        self.test_run_config.save()

        first_test_run_response = self.submit_solution(is_testrun=True)
        second_test_run_response = self.submit_solution(is_testrun=True)

        self.assertNotRegex(
            first_test_run_response.content.decode('utf-8'), 'limit.*exceeded'
        )
        self.assertNotRegex(
            second_test_run_response.content.decode('utf-8'), 'limit.*exceeded'
        )
