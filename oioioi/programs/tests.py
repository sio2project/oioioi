import os
import re
from collections import defaultdict
from datetime import datetime, timezone, timedelta  # pylint: disable=E0611

import pytest
import six
import urllib
import yaml

from django.conf import settings
from django.contrib.admin.utils import quote
from django.contrib.auth.models import User
from django.core.exceptions import ImproperlyConfigured
from django.core.files.base import ContentFile
from django.test import RequestFactory
from django.test.utils import override_settings
from django.urls import reverse
from django.utils.html import escape, strip_tags
from django.utils.http import urlencode
from django.utils import timezone as django_timezone
from oioioi.base.notification import NotificationHandler
from oioioi.base.tests import (
    TestCase,
    check_is_accessible,
    check_not_accessible,
    fake_time,
)
from oioioi.base.utils import memoized_property
from oioioi.base.utils.test_migrations import TestCaseMigrations
from oioioi.contests.models import Contest, ProblemInstance, Round, Submission
from oioioi.contests.scores import IntegerScore
from oioioi.contests.handlers import send_notification_judged
from oioioi.contests.tests import PrivateRegistrationController, SubmitMixin
from oioioi.filetracker.tests import TestStreamingMixin
from oioioi.problems.models import Problem
from oioioi.programs import utils
from oioioi.programs.controllers import ProgrammingContestController
from oioioi.programs.handlers import collect_tests
from oioioi.programs.models import (
    ModelSolution,
    ProblemAllowedLanguage,
    ProgramSubmission,
    ReportActionsConfig,
    Test,
    LanguageOverrideForTest,
    TestReport,
    check_compilers_config,
)
from oioioi.programs.problem_instance_utils import get_allowed_languages_dict
from oioioi.programs.utils import form_field_id_for_langs
from oioioi.programs.views import _testreports_to_generate_outs
from oioioi.sinolpack.models import ExtraConfig
from oioioi.sinolpack.tests import get_test_filename
from oioioi.evalmgr.tasks import create_environ


def extract_code(show_response):
    open_pre_start = show_response.content.find(b'<pre') + len(b'<pre')
    open_pre_end = show_response.content.find(b'>', open_pre_start) + 1
    close_pre_start = show_response.content.find(b'</pre>', open_pre_end)
    # Get substring and strip tags.
    show_response.content = strip_tags(
        six.ensure_text(
            show_response.content[open_pre_end:close_pre_start], errors="replace"
        )
    )


def extract_code_from_diff(show_response):
    pre_first = show_response.content.find(b'</pre>') + len(b'</pre>')
    pre_start = show_response.content.find(b'<pre>', pre_first) + len(b'<pre>')
    pre_end = show_response.content.find(b'</pre>', pre_first)
    # Get substring and strip tags.
    show_response.content = strip_tags(
        six.ensure_text(show_response.content[pre_start:pre_end], errors="replace")
    )


class SubmitFileMixin(SubmitMixin):
    def submit_file(
        self,
        contest,
        problem_instance,
        file_size=1024,
        file_name='submission.cpp',
        kind='NORMAL',
        user=None,
    ):
        url = reverse('submit', kwargs={'contest_id': contest.id})

        file = ContentFile(b'a' * file_size, name=file_name)
        post_data = {'problem_instance_id': problem_instance.id, 'file': file}

        if user:
            post_data.update({'kind': kind, 'user': user})
        return self.client.post(url, post_data)

    def submit_code(
        self,
        contest,
        problem_instance,
        code='',
        prog_lang='C',
        send_file=False,
        kind='NORMAL',
        user=None,
    ):
        url = reverse('submit', kwargs={'contest_id': contest.id})
        file = ''
        if send_file:
            file = ContentFile('a' * 1024, name='a.c')
        langs_field_name = form_field_id_for_langs(problem_instance)

        post_data = {
            'problem_instance_id': problem_instance.id,
            'file': file,
            'code': code,
            langs_field_name: prog_lang,
        }
        if user:
            post_data.update({'kind': kind, 'user': user})
        return self.client.post(url, post_data)


class TestProgrammingProblemController(TestCase):
    fixtures = [
        'test_users',
        'test_contest',
        'test_full_package',
        'test_problem_instance',
    ]

    def test_safe_exec_mode(self):
        problem_instance = ProblemInstance.objects.get(pk=1)
        self.assertEqual(problem_instance.controller.get_safe_exec_mode(), 'sio2jail')


class TestProgrammingContestController(TestCase):
    fixtures = [
        'test_users',
        'test_contest',
        'test_full_package',
        'test_problem_instance',
    ]

    def test_safe_exec_mode(self):
        # CAUTION: 'sio2jail' is default value with an important reason.
        #          CHANGE ONLY IF YOU KNOW WHAT YOU ARE DOING.
        #          If you do so, don't forget to update another controllers
        #          which are using default value and have to use 'sio2jail' mode
        #          like OIContestController and TeacherContestController.
        contest = Contest.objects.get()
        self.assertEqual(contest.controller.get_safe_exec_mode(), 'sio2jail')


class TestProgramsViews(TestCase, TestStreamingMixin):
    fixtures = [
        'test_users',
        'test_contest',
        'test_full_package',
        'test_problem_instance',
        'test_permissions',
        'test_submission',
    ]

    def test_submission_views(self):
        self.assertTrue(self.client.login(username='test_user'))
        submission = ProgramSubmission.objects.get(pk=1)
        kwargs = {
            'contest_id': submission.problem_instance.contest.id,
            'submission_id': submission.id,
        }
        # Download shown response.
        show_response = self.client.get(
            reverse('show_submission_source', kwargs=kwargs)
        )
        self.assertEqual(show_response.status_code, 200)
        # Download plain text response.
        download_response = self.client.get(
            reverse('download_submission_source', kwargs=kwargs)
        )
        # Extract code from <pre>'s
        extract_code(show_response)
        # Shown code has entities like &gt; - let's escape the plaintext.
        download_response_content = escape(
            self.streamingContent(download_response).decode('utf-8')
        )
        # Now it should work.
        self.assertEqual(download_response.status_code, 200)
        self.assertTrue(download_response.streaming)
        self.assertEqual(
            show_response.content.decode('utf-8'), download_response_content
        )
        self.assertIn('main()', show_response.content.decode('utf-8'))
        self.assertTrue(show_response.content.strip().endswith(b'}'))
        self.assertTrue(
            download_response['Content-Disposition'].startswith('attachment')
        )

    def test_test_views(self):
        self.assertTrue(self.client.login(username='test_admin'))
        self.client.get('/c/c/')  # 'c' becomes the current contest

        test = Test.objects.get(name='0')
        kwargs = {'test_id': test.id}
        response = self.client.get(reverse('download_input_file', kwargs=kwargs))
        self.assertStreamingEqual(response, b'1 2\n')
        response = self.client.get(reverse('download_output_file', kwargs=kwargs))
        self.assertStreamingEqual(response, b'3\n')

    def test_submissions_permissions(self):
        submission = Submission.objects.get(pk=1)
        test = Test.objects.get(name='0')
        for view in ['show_submission_source', 'download_submission_source']:
            check_not_accessible(
                self,
                view,
                kwargs={
                    'contest_id': submission.problem_instance.contest.id,
                    'submission_id': submission.id,
                },
            )
        check_not_accessible(
            self,
            'source_diff',
            kwargs={
                'contest_id': submission.problem_instance.contest.id,
                'submission1_id': submission.id,
                'submission2_id': submission.id,
            },
        )
        for view in ['download_input_file', 'download_output_file']:
            check_not_accessible(self, view, kwargs={'test_id': test.id})
        self.assertTrue(self.client.login(username='test_user'))
        for view in ['download_input_file', 'download_output_file']:
            check_not_accessible(self, view, kwargs={'test_id': test.id})
        self.assertTrue(self.client.login(username='test_contest_admin'))
        for view in ['download_input_file', 'download_output_file']:
            url = reverse(view, kwargs={'test_id': test.id})
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)

    def test_model_solutions_view(self):
        pi = ProblemInstance.objects.get()
        ModelSolution.objects.recreate_model_submissions(pi)

        self.client.get('/c/c/')  # 'c' becomes the current contest
        url = reverse('model_solutions', args=(pi.id,))

        self.assertTrue(self.client.login(username='test_admin'))
        response = self.client.get(url)

        no_whitespaces_content = re.sub(r"\s*", "", response.content.decode('utf-8'))
        for element in ['>sum<', '>sumb0<', '>sums1<', '>100<', '>0<']:
            self.assertIn(element, no_whitespaces_content)

        self.assertNotContains(response, 'submission--INI_OK')
        self.assertContains(response, 'submission--INI_ERR', count=1)
        self.assertContains(response, 'submission--OK25', count=8)
        self.assertContains(response, 'submission--WA', count=5)
        self.assertContains(response, 'submission--CE', count=1)

        self.assertNotContains(response, 'submission--WA25')
        self.assertNotContains(response, 'submission--WA50')
        self.assertNotContains(response, 'submission-- ')
        self.assertNotContains(response, 'submission-- ')

        self.assertEqual(no_whitespaces_content.count('>10.00s<'), 5)


class TestSourceWithoutContest(TestCase):
    fixtures = [
        'test_users',
        'test_problem_instance_without_contest',
        'test_submission_source',
        'test_full_package',
    ]

    # Regressive test for SIO-2211.
    def test_source_permissions(self):
        submission = Submission.objects.get(pk=1)

        self.assertTrue(self.client.login(username='test_user'))
        check_is_accessible(
            self, 'show_submission_source', kwargs={'submission_id': submission.id}
        )

        self.assertTrue(self.client.login(username='test_admin'))
        check_is_accessible(
            self, 'show_submission_source', kwargs={'submission_id': submission.id}
        )

        self.assertTrue(self.client.login(username='test_user2'))
        check_not_accessible(
            self, 'show_submission_source', kwargs={'submission_id': submission.id}
        )


class TestHeaderLinks(TestCase):
    fixtures = [
        'test_users',
        'test_contest',
        'test_full_package',
        'test_problem_instance',
        'test_submission',
    ]

    def test_link_to_changelist_visibility(self):
        submission = Submission.objects.get(pk=1)
        kwargs = {
            'contest_id': submission.problem_instance.contest.id,
            'submission_id': submission.id,
        }

        # First check if admin can see the link.
        self.assertTrue(self.client.login(username='test_admin'))
        response = self.client.get(reverse('submission', kwargs=kwargs))
        link_url = reverse('oioioiadmin:contests_submission_changelist')
        link_url += "?" + urlencode({'pi': submission.problem_instance.problem.name})
        self.assertContains(
            response,
            '<a href="{}">{}</a>'.format(link_url, submission.problem_instance),
            html=True,
        )

        # And if normal user can't see it. Check just for href.
        self.assertTrue(self.client.login(username='test_user'))
        response = self.client.get(reverse('submission', kwargs=kwargs))
        self.assertNotContains(response, '<a href="{}">'.format(link_url), html=True)


class TestProgramsXssViews(TestCase, TestStreamingMixin):
    fixtures = [
        'test_users',
        'test_contest',
        'test_full_package',
        'test_problem_instance',
        'test_submission_xss',
    ]

    def test_submission_xss_views(self):
        self.assertTrue(self.client.login(username='test_user'))
        submission = Submission.objects.get(pk=1)
        kwargs = {
            'contest_id': submission.problem_instance.contest.id,
            'submission_id': submission.id,
        }
        # Download shown response.
        show_response = self.client.get(
            reverse('show_submission_source', kwargs=kwargs)
        )
        # Download plain text response.
        download_response = self.client.get(
            reverse('download_submission_source', kwargs=kwargs)
        )
        # Get code from diff view
        diff_response = self.client.get(
            reverse(
                'source_diff',
                kwargs={
                    'contest_id': submission.problem_instance.contest.id,
                    'submission1_id': submission.id,
                    'submission2_id': submission.id,
                },
            )
        )
        # Response status before extract_code
        self.assertEqual(show_response.status_code, 200)
        self.assertEqual(diff_response.status_code, 200)
        # Extract code from <pre>'s
        extract_code(show_response)
        extract_code_from_diff(diff_response)
        # Shown code has entities like &gt; - let's escape the plaintext.
        download_response_content = escape(
            self.streamingContent(download_response).decode('utf-8')
        )
        # Now it should work.
        self.assertEqual(download_response.status_code, 200)
        self.assertTrue(download_response.streaming)
        self.assertEqual(
            show_response.content.decode('utf-8'), download_response_content
        )
        self.assertNotContains(show_response, u'<script>')
        self.assertNotContains(diff_response, u'<script>')
        self.assertNotIn(download_response_content, u'<script>')
        self.assertContains(show_response, 'main()')
        self.assertContains(diff_response, 'main()')
        self.assertTrue(show_response.content.strip().endswith(b'}'))
        self.assertTrue(diff_response.content.strip().endswith(b'}'))
        self.assertTrue(
            download_response['Content-Disposition'].startswith('attachment')
        )


class TestOtherSubmissions(TestCase):
    fixtures = [
        'test_users',
        'test_contest',
        'test_full_package',
        'test_problem_instance',
        'test_submission',
        'test_submissions_CE',
    ]

    def _test_get(self, username):
        self.assertTrue(self.client.login(username=username))
        submission = Submission.objects.get(pk=1)
        kwargs = {
            'contest_id': submission.problem_instance.contest.id,
            'submission_id': submission.id,
        }
        response = self.client.get(reverse('submission', kwargs=kwargs))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Other submissions for this problem')
        self.assertContains(response, 'submission--OK')
        self.assertContains(response, 'submission--CE')

    def test_admin(self):
        self._test_get('test_admin')

    def test_user(self):
        self._test_get('test_user')


class TestNoOtherSubmissions(TestCase):
    fixtures = [
        'test_users',
        'test_contest',
        'test_full_package',
        'test_problem_instance',
        'test_submission',
    ]

    def _test_get(self, username):
        self.assertTrue(self.client.login(username=username))
        submission = Submission.objects.get(pk=1)
        kwargs = {
            'contest_id': submission.problem_instance.contest.id,
            'submission_id': submission.id,
        }
        response = self.client.get(reverse('submission', kwargs=kwargs))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'Other submissions for this problem')
        self.assertContains(response, 'submission--OK')

    def test_admin(self):
        self._test_get('test_admin')

    def test_user(self):
        self._test_get('test_user')


class TestDiffView(TestCase):
    fixtures = [
        'test_users',
        'test_contest',
        'test_full_package',
        'test_problem_instance',
        'test_submission',
        'test_another_submission',
    ]

    def test_saving_button(self):
        self.assertTrue(self.client.login(username='test_admin'))
        submission = Submission.objects.get(pk=1)
        submission2 = Submission.objects.get(pk=2)
        kwargs = {
            'contest_id': submission.problem_instance.contest.id,
            'submission_id': submission.id,
        }
        response = self.client.get(reverse('submission', kwargs=kwargs))
        self.assertContains(response, 'id="diff-button-save"')
        response = self.client.get(reverse('save_diff_id', kwargs=kwargs))
        self.assertEqual(response.status_code, 200)
        response = self.client.get(reverse('submission', kwargs=kwargs))
        self.assertContains(response, 'id="diff-button-do"')
        kwargs2 = {
            'contest_id': submission.problem_instance.contest.id,
            'submission1_id': submission2.id,
            'submission2_id': submission.id,
        }
        self.assertContains(response, reverse('source_diff', kwargs=kwargs2))
        response = self.client.get(reverse('source_diff', kwargs=kwargs2))
        self.assertEqual(response.status_code, 200)
        response = self.client.get(reverse('submission', kwargs=kwargs))
        self.assertContains(response, 'id="diff-button-save"')

    def test_diff_view(self):
        self.assertTrue(self.client.login(username='test_admin'))
        submission1 = Submission.objects.get(pk=1)
        submission2 = Submission.objects.get(pk=2)
        kwargs = {
            'contest_id': submission1.problem_instance.contest.id,
            'submission1_id': submission1.id,
            'submission2_id': submission2.id,
        }
        kwargsrev = {
            'contest_id': submission1.problem_instance.contest.id,
            'submission1_id': submission2.id,
            'submission2_id': submission1.id,
        }
        response = self.client.get(reverse('source_diff', kwargs=kwargs))
        self.assertContains(response, reverse('source_diff', kwargs=kwargsrev))
        self.assertContains(response, 'diff-highlight diff-highlight__line left')
        self.assertContains(response, 'diff-highlight diff-highlight__line right')
        self.assertContains(response, 'diff-highlight diff-highlight__num left')
        self.assertContains(response, 'diff-highlight diff-highlight__num right')


class TestSubmission(TestCase, SubmitFileMixin):
    fixtures = [
        'test_users',
        'test_contest',
        'test_full_package',
        'test_problem_instance',
        'test_submission',
        'test_extra_problem',
    ]

    def setUp(self):
        self.assertTrue(self.client.login(username='test_user'))

    @override_settings(TIME_ZONE="Europe/Warsaw")
    def test_submission_completed_notification(self):
        msg_count = defaultdict(int)
        messages = []

        @classmethod
        def fake_send_notification(
            cls,
            user,
            notification_type,
            notification_message,
            notificaion_message_arguments,
        ):
            if user.pk == 1002:
                msg_count['user_1002_notifications'] += 1
            if user.pk == 1001:
                msg_count['user_1001_notifications'] += 1
            messages.append((notification_message, notificaion_message_arguments))

        send_notification_backup = NotificationHandler.send_notification
        NotificationHandler.send_notification = fake_send_notification

        submission = Submission.objects.get(pk=1)
        
        environ = create_environ()
        environ['extra_args'] = {}
        environ['is_rejudge'] = False
        environ['submission_id'] = submission.pk
        environ['contest_id'] = submission.problem_instance.contest.id
        send_notification_judged(environ)

        # Check if a notification for user 1001 was send
        # And user 1002 doesn't received a notification
        self.assertEqual(len(messages), 1)
        self.assertEqual(msg_count['user_1001_notifications'], 1)
        self.assertEqual(msg_count['user_1002_notifications'], 0)

        environ['is_rejudge'] = True
        send_notification_judged(environ)
        self.assertEqual(len(messages), 1)

        environ['is_rejudge'] = False
        # Results barely not available, should catch timezone-related errors
        Round.objects.update(
            results_date=django_timezone.now()+timedelta(minutes=30)
        )
        send_notification_judged(environ)
        self.assertEqual(len(messages), 1)

        Round.objects.update(results_date=None)
        send_notification_judged(environ)
        self.assertEqual(len(messages), 1)

        self.assertIn('%(score)s', messages[0][0])
        self.assertIn('score', messages[0][1])
        self.assertEqual(messages[0][1]['score'], '34')
        self.assertIn('was judged', messages[0][0])
        self.assertNotIn('Initial result', messages[0][0])

        NotificationHandler.send_notification = send_notification_backup

    @override_settings(WARN_ABOUT_REPEATED_SUBMISSION=True)
    def test_repeated_submission_fail(self):
        contest = Contest.objects.get()
        problem_instance = ProblemInstance.objects.get(pk=1)
        response = self.submit_file(contest, problem_instance)
        response = self.submit_file(contest, problem_instance)
        self.assertEqual(200, response.status_code)
        self.assertContains(response, 'Please resubmit')

    @override_settings(WARN_ABOUT_REPEATED_SUBMISSION=True)
    def test_repeated_submission_different_problems(self):
        contest = Contest.objects.get()
        problem_instance1 = ProblemInstance.objects.get(pk=1)
        problem_instance2 = ProblemInstance.objects.get(pk=2)
        response = self.submit_file(contest, problem_instance1)
        response = self.submit_file(contest, problem_instance2)
        self._assertSubmitted(contest, response)

    @override_settings(WARN_ABOUT_REPEATED_SUBMISSION=True)
    def test_repeated_submission_success(self):
        contest = Contest.objects.get()
        problem_instance = ProblemInstance.objects.get(pk=1)
        response = self.submit_file(contest, problem_instance)
        response = self.submit_file(contest, problem_instance)
        response = self.submit_file(contest, problem_instance)
        self._assertSubmitted(contest, response)

    def test_simple_submission(self):
        contest = Contest.objects.get()
        problem_instance = ProblemInstance.objects.get(pk=1)
        round = Round.objects.get()
        round.start_date = datetime(2012, 7, 31, tzinfo=timezone.utc)
        round.end_date = datetime(2012, 8, 10, tzinfo=timezone.utc)
        round.save()

        with fake_time(datetime(2012, 7, 10, tzinfo=timezone.utc)):
            response = self.submit_file(contest, problem_instance)
            self.assertEqual(200, response.status_code)
            self.assertContains(response, 'Sorry, there are no problems')

        with fake_time(datetime(2012, 7, 31, tzinfo=timezone.utc)):
            response = self.submit_file(contest, problem_instance)
            self._assertSubmitted(contest, response)

        with fake_time(datetime(2012, 8, 5, tzinfo=timezone.utc)):
            response = self.submit_file(contest, problem_instance)
            self._assertSubmitted(contest, response)

        with fake_time(datetime(2012, 8, 10, tzinfo=timezone.utc)):
            response = self.submit_file(contest, problem_instance)
            self._assertSubmitted(contest, response)

        with fake_time(datetime(2012, 8, 11, tzinfo=timezone.utc)):
            response = self.submit_file(contest, problem_instance)
            self.assertEqual(200, response.status_code)
            self.assertContains(response, 'Sorry, there are no problems')

    def _set_code_size_limit(self, limit):
        ec = ExtraConfig.objects.get()
        conf = ec.parsed_config
        conf['submission_size_limit'] = limit
        ec.config = yaml.dump(conf)
        ec.save()

    def test_huge_submission(self):
        contest = Contest.objects.get()
        problem_instance = ProblemInstance.objects.get(pk=1)
        response = self.submit_file(contest, problem_instance, file_size=102405)
        self.assertContains(response, 'File size limit exceeded.')
        self.assertNotContains(response, 'You have to either choose file or paste')
        self._set_code_size_limit(102404)
        response = self.submit_file(contest, problem_instance, file_size=102405)
        self.assertContains(response, 'File size limit exceeded.')
        self._set_code_size_limit(102405)
        response = self.submit_file(contest, problem_instance, file_size=102405)
        self.assertEqual(response.status_code, 302);

    def test_huge_code_length(self):
        contest = Contest.objects.get()
        problem_instance = ProblemInstance.objects.get(pk=1)
        code = 'a' * 102401
        response = self.submit_code(contest, problem_instance, code=code)
        self.assertContains(response, 'Code length limit exceeded.')
        self._set_code_size_limit(102400)
        response = self.submit_code(contest, problem_instance, code=code)
        self.assertContains(response, 'Code length limit exceeded.')
        self._set_code_size_limit(102401)
        response = self.submit_code(contest, problem_instance, code=code)
        self.assertEqual(response.status_code, 302);

    def test_size_limit_accuracy(self):
        contest = Contest.objects.get()
        problem_instance = ProblemInstance.objects.get(pk=1)
        response = self.submit_file(contest, problem_instance, file_size=102400)
        self._assertSubmitted(contest, response)

    def test_submissions_limitation(self):
        contest = Contest.objects.get()
        problem_instance = ProblemInstance.objects.get(pk=1)
        problem_instance.submissions_limit = 2
        problem_instance.save()
        response = self.submit_file(contest, problem_instance)
        self._assertSubmitted(contest, response)
        response = self.submit_file(contest, problem_instance)
        self.assertEqual(200, response.status_code)
        self.assertContains(response, 'Submission limit for the problem')

    def _assertUnsupportedExtension(self, contest, problem_instance, name, ext):
        response = self.submit_file(
            contest, problem_instance, file_name='%s.%s' % (name, ext)
        )
        self.assertContains(response, 'Unknown or not supported file extension.')

    def test_extension_checking(self):
        contest = Contest.objects.get()
        problem_instance = ProblemInstance.objects.get(pk=1)
        self._assertUnsupportedExtension(contest, problem_instance, 'xxx', '')
        self._assertUnsupportedExtension(contest, problem_instance, 'xxx', 'e')
        self._assertUnsupportedExtension(contest, problem_instance, 'xxx', 'cppp')
        response = self.submit_file(contest, problem_instance, file_name='a.tar.cpp')
        self._assertSubmitted(contest, response)

    def test_code_pasting(self):
        contest = Contest.objects.get()
        problem_instance = ProblemInstance.objects.get(pk=1)
        response = self.submit_code(contest, problem_instance, 'some code')
        self._assertSubmitted(contest, response)
        response = self.submit_code(contest, problem_instance, 'some code', '')
        self.assertContains(response, 'You have to choose programming language.')
        response = self.submit_code(contest, problem_instance, '')
        self.assertContains(response, 'You have to either choose file or paste code.')
        response = self.submit_code(
            contest, problem_instance, 'some code', send_file=True
        )
        self.assertContains(response, 'You have to either choose file or paste code.')

    @override_settings(WARN_ABOUT_REPEATED_SUBMISSION=True)
    def test_pasting_unicode_code(self):
        contest = Contest.objects.get()
        problem_instance = ProblemInstance.objects.get(pk=1)
        response = self.submit_code(
            contest, problem_instance, chr(12345), user='test_user'
        )
        self._assertSubmitted(contest, response)

    def test_limiting_extensions(self):
        contest = Contest.objects.get()
        problem_instance = ProblemInstance.objects.get(pk=1)
        self._assertUnsupportedExtension(
            contest, problem_instance, 'xxx', 'inv4l1d_3xt'
        )
        response = self.submit_file(contest, problem_instance, file_name='a.c')
        self._assertSubmitted(contest, response)


class TestSubmissionAdmin(TestCase):
    fixtures = [
        'test_users',
        'test_contest',
        'test_full_package',
        'test_problem_instance',
        'test_submission',
    ]

    def test_submissions_changelist(self):
        self.assertTrue(self.client.login(username='test_admin'))
        pi = ProblemInstance.objects.get()
        ModelSolution.objects.recreate_model_submissions(pi)

        self.client.get('/c/c/')  # 'c' becomes the current contest
        url = reverse('oioioiadmin:contests_submission_changelist')

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '(sum.c)')
        self.assertContains(response, 'test_user')
        self.assertContains(response, 'submission--OK')
        self.assertContains(response, 'submission_diff_action')


class TestSubmittingAsAdmin(TestCase):
    fixtures = [
        'test_users',
        'test_contest',
        'test_problem_instance',
        'test_full_package',
    ]

    def test_ignored_submission(self):
        self.assertTrue(self.client.login(username='test_user'))
        contest = Contest.objects.get()
        pi = ProblemInstance.objects.get()
        url = reverse('submit', kwargs={'contest_id': contest.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'IGNORED')

        self.assertTrue(self.client.login(username='test_admin'))
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'IGNORED')

        data = {
            'problem_instance_id': pi.id,
            'file': open(get_test_filename('sum-various-results.cpp'), 'rb'),
            'user': 'test_user',
            'kind': 'IGNORED',
        }
        response = self.client.post(url, data, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Submission.objects.count(), 1)
        submission = Submission.objects.get()
        self.assertEqual(submission.user.username, 'test_user')
        self.assertEqual(submission.kind, 'IGNORED')

        url = reverse('default_ranking', kwargs={'contest_id': contest.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'Test User')

        self.assertTrue(self.client.login(username='test_user'))
        url = reverse('my_submissions', kwargs={'contest_id': contest.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Ignored')

    def test_submitting_as_self(self):
        self.assertTrue(self.client.login(username='test_admin'))
        contest = Contest.objects.get()
        pi = ProblemInstance.objects.get()
        url = reverse('submit', kwargs={'contest_id': contest.id})

        self.assertTrue(self.client.login(username='test_admin'))
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'IGNORED')
        self.assertContains(response, 'NORMAL')

        f = open(get_test_filename('sum-various-results.cpp'), 'rb')
        data = {
            'problem_instance_id': pi.id,
            'file': f,
            'user': 'test_admin',
            'kind': 'NORMAL',
        }
        response = self.client.post(url, data, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Submission.objects.count(), 1)
        submission = Submission.objects.get()
        self.assertEqual(submission.user.username, 'test_admin')
        self.assertEqual(submission.kind, 'NORMAL')

        ps = ProgramSubmission.objects.get()
        f.seek(0, os.SEEK_END)
        self.assertEqual(ps.source_length, f.tell())

        url = reverse('default_ranking', kwargs={'contest_id': contest.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'Test Admin')
        self.assertContains(response, 'no one in this ranking')


class PrivateProgrammingContestController(ProgrammingContestController):
    def registration_controller(self):
        return PrivateRegistrationController(self.contest)


class TestSubmittingAsContestAdmin(TestCase):
    fixtures = [
        'test_users',
        'test_contest',
        'test_full_package',
        'test_problem_instance',
        'test_permissions',
    ]

    def test_missing_permission(self):
        contest = Contest.objects.get()
        contest.controller_name = (
            'oioioi.programs.tests.PrivateProgrammingContestController'
        )
        contest.save()
        pi = ProblemInstance.objects.get()
        url = reverse('submit', kwargs={'contest_id': contest.id})

        self.assertTrue(self.client.login(username='test_contest_admin'))
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'IGNORED')

        data = {
            'problem_instance_id': pi.id,
            'file': open(get_test_filename('sum-various-results.cpp'), 'rb'),
            'user': 'test_user',
            'kind': 'NORMAL',
        }
        response = self.client.post(url, data, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Submission.objects.count(), 0)
        self.assertContains(response, 'enough privileges')


class TestSubmittingAsObserver(TestCase):
    fixtures = [
        'test_users',
        'test_contest',
        'test_full_package',
        'test_problem_instance',
        'test_permissions',
    ]

    def test_ignored_submission(self):
        self.assertTrue(self.client.login(username='test_observer'))
        contest = Contest.objects.get()
        pi = ProblemInstance.objects.get()
        url = reverse('submit', kwargs={'contest_id': contest.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'IGNORED')

        data = {
            'problem_instance_id': pi.id,
            'file': open(get_test_filename('sum-various-results.cpp'), 'rb'),
        }
        response = self.client.post(url, data, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Submission.objects.count(), 1)
        submission = Submission.objects.get()
        self.assertEqual(submission.user.username, 'test_observer')
        self.assertEqual(submission.kind, 'IGNORED')

        url = reverse('default_ranking', kwargs={'contest_id': contest.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'Test Observer')

        url = reverse('my_submissions', kwargs={'contest_id': contest.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Ignored')


class TestNotifications(TestCase):
    fixtures = [
        'test_users',
        'test_contest',
        'test_full_package',
        'test_problem_instance',
        'test_permissions',
        'test_submission',
    ]

    def test_initial_results_notification(self):
        msg_count = defaultdict(int)
        messages = []

        @classmethod
        def fake_send_notification(
            cls,
            user,
            notification_type,
            notification_message,
            notificaion_message_arguments,
        ):
            if user.pk == 1001 and notification_type == 'initial_results':
                msg_count['user_1001_notifications'] += 1
            messages.append((notification_message, notificaion_message_arguments))

        send_notification_backup = NotificationHandler.send_notification
        NotificationHandler.send_notification = fake_send_notification
        environ = {
            'compilation_result': 'OK',
            'submission_id': 1,
            'status': 'OK',
            'score': None,
            'max_score': None,
            'compilation_message': '',
            'tests': {},
            'is_rejudge': False,
        }

        send_notification_judged(environ, 'INITIAL')
        # Check if a notification for user 1001 was sent
        self.assertEqual(msg_count['user_1001_notifications'], 1)

        environ['status'] = 'CE'
        send_notification_judged(environ, 'INITIAL')
        # We should send a notif even for non-compiling submissions
        self.assertEqual(msg_count['user_1001_notifications'], 2)

        environ['is_rejudge'] = True
        send_notification_judged(environ, 'INITIAL')
        # No notification should be sent for a rejudge
        self.assertEqual(msg_count['user_1001_notifications'], 2)

        self.assertIn('Initial result', messages[0][0])
        self.assertNotIn('was judged', messages[0][0])

        NotificationHandler.send_notification = send_notification_backup


class TestScorers(TestCase):
    t_results_ok = (
        (
            {'exec_time_limit': 100, 'max_score': 100},
            {'result_code': 'OK', 'time_used': 0},
        ),
        (
            {'exec_time_limit': 100, 'max_score': 100},
            {'result_code': 'OK', 'time_used': 50},
        ),
        (
            {'exec_time_limit': 1000, 'max_score': 100},
            {'result_code': 'OK', 'time_used': 501},
        ),
        (
            {'exec_time_limit': 100, 'max_score': 100},
            {'result_code': 'OK', 'time_used': 75},
        ),
        (
            {'exec_time_limit': 1000, 'max_score': 100},
            {'result_code': 'OK', 'time_used': 999},
        ),
        ({'max_score': 100}, {'result_code': 'OK', 'time_used': 0}),
        ({'max_score': 100}, {'result_code': 'OK', 'time_used': 99999}),
    )

    t_results_ok_perc = (
        (
            {'exec_time_limit': 100, 'max_score': 100},
            {'result_code': 'OK', 'time_used': 0, 'result_percentage': (99, 1)},
        ),
        (
            {'exec_time_limit': 100, 'max_score': 100},
            {'result_code': 'OK', 'time_used': 75, 'result_percentage': (50, 1)},
        ),
        (
            {'exec_time_limit': 100, 'max_score': 100},
            {'result_code': 'OK', 'time_used': 75, 'result_percentage': (0, 1)},
        ),
        (
            {'exec_time_limit': 100, 'max_score': 100},
            {'result_code': 'OK', 'time_used': 99, 'result_percentage': (1, 1)},
        ),
    )

    t_results_unequal_max_scores = (
        (
            {'exec_time_limit': 100, 'max_score': 10},
            {'result_code': 'OK', 'time_used': 10},
        ),
        (
            {'exec_time_limit': 1000, 'max_score': 20},
            {'result_code': 'WA', 'time_used': 50},
        ),
    )

    t_expected_unequal_max_scores = [
        (IntegerScore(10), IntegerScore(10), 'OK'),
        (IntegerScore(0), IntegerScore(20), 'WA'),
    ]

    t_results_wrong = [
        (
            {'exec_time_limit': 100, 'max_score': 100},
            {'result_code': 'WA', 'time_used': 75},
        ),
        (
            {'exec_time_limit': 100, 'max_score': 100},
            {'result_code': 'RV', 'time_used': 75},
        ),
    ]

    t_expected_wrong = [
        (IntegerScore(0), IntegerScore(100), 'WA'),
        (IntegerScore(0), IntegerScore(100), 'RV'),
    ]

    def test_discrete_test_scorer(self):
        exp_scores = [100] * len(self.t_results_ok)
        exp_max_scores = [100] * len(self.t_results_ok)
        exp_statuses = ['OK'] * len(self.t_results_ok)
        expected = list(zip(exp_scores, exp_max_scores, exp_statuses))

        results = list(map(utils.discrete_test_scorer, *list(zip(*self.t_results_ok))))
        self.assertEqual(expected, results)

        results = list(
            map(utils.discrete_test_scorer, *list(zip(*self.t_results_wrong)))
        )
        self.assertEqual(self.t_expected_wrong, results)

        results = list(
            map(
                utils.discrete_test_scorer,
                *list(zip(*self.t_results_unequal_max_scores))
            )
        )
        self.assertEqual(self.t_expected_unequal_max_scores, results)

    def test_threshold_linear_test_scorer(self):
        exp_scores = [100, 100, 99, 50, 1, 100, 100]
        exp_max_scores = [100] * len(self.t_results_ok)
        exp_statuses = ['OK'] * len(self.t_results_ok)
        expected = list(zip(exp_scores, exp_max_scores, exp_statuses))

        results = list(
            map(utils.threshold_linear_test_scorer, *list(zip(*self.t_results_ok)))
        )
        self.assertEqual(expected, results)

        exp_scores = [99, 25, 0, 1]
        exp_max_scores = [100] * len(self.t_results_ok_perc)
        exp_statuses = ['OK'] * len(self.t_results_ok_perc)
        expected = list(zip(exp_scores, exp_max_scores, exp_statuses))

        results = list(
            map(utils.threshold_linear_test_scorer, *list(zip(*self.t_results_ok_perc)))
        )
        self.assertEqual(expected, results)

        malformed = (
            {'exec_time_limit': 100, 'max_score': 100},
            {'result_code': 'OK', 'time_used': 101},
        )
        self.assertEqual(
            utils.threshold_linear_test_scorer(*malformed), (0, 100, 'TLE')
        )

        results = list(
            map(utils.threshold_linear_test_scorer, *list(zip(*self.t_results_wrong)))
        )
        self.assertEqual(self.t_expected_wrong, results)

        results = list(
            map(
                utils.threshold_linear_test_scorer,
                *list(zip(*self.t_results_unequal_max_scores))
            )
        )
        self.assertEqual(self.t_expected_unequal_max_scores, results)

    @memoized_property
    def g_results_ok(self):
        # Tested elsewhere
        results = list(
            map(utils.threshold_linear_test_scorer, *list(zip(*self.t_results_ok[:4])))
        )
        dicts = [
            dict(score=sc.serialize(), max_score=msc.serialize(), status=st, order=i)
            for i, (sc, msc, st) in enumerate(results)
        ]
        return dict(list(zip(list(range(len(dicts))), dicts)))

    @memoized_property
    def g_results_wrong(self):
        results = list(
            map(utils.threshold_linear_test_scorer, *list(zip(*self.t_results_wrong)))
        )
        dicts = list(self.g_results_ok.values())
        dicts += [
            dict(
                score=sc.serialize(),
                max_score=msc.serialize(),
                status=st,
                order=(i + 10),
            )
            for i, (sc, msc, st) in enumerate(results)
        ]
        return dict(list(zip(list(range(len(dicts))), dicts)))

    @memoized_property
    def g_results_unequal_max_scores(self):
        results = list(
            map(
                utils.threshold_linear_test_scorer,
                *list(zip(*self.t_results_unequal_max_scores))
            )
        )
        dicts = list(self.g_results_wrong.values())
        dicts += [
            dict(
                score=sc.serialize(),
                max_score=msc.serialize(),
                status=st,
                order=(i + 20),
            )
            for i, (sc, msc, st) in enumerate(results)
        ]
        return dict(list(zip(list(range(len(dicts))), dicts)))

    def test_min_group_scorer(self):
        self.assertEqual((50, 100, 'OK'), utils.min_group_scorer(self.g_results_ok))
        self.assertEqual((0, 100, 'WA'), utils.min_group_scorer(self.g_results_wrong))
        with self.assertRaises(utils.UnequalMaxScores):
            utils.min_group_scorer(self.g_results_unequal_max_scores)

    def test_sum_group_scorer(self):
        self.assertEqual((349, 400, 'OK'), utils.sum_group_scorer(self.g_results_ok))
        self.assertEqual((349, 600, 'WA'), utils.sum_group_scorer(self.g_results_wrong))
        self.assertEqual(
            (359, 630, 'WA'), utils.sum_group_scorer(self.g_results_unequal_max_scores)
        )

    def test_sum_score_aggregator(self):
        self.assertEqual(
            (349, 400, 'OK'), utils.sum_score_aggregator(self.g_results_ok)
        )
        self.assertEqual(
            (349, 600, 'WA'), utils.sum_score_aggregator(self.g_results_wrong)
        )
        self.assertEqual(
            (359, 630, 'WA'),
            utils.sum_score_aggregator(self.g_results_unequal_max_scores),
        )


class TestUserOutsGenerating(TestCase):
    fixtures = [
        'test_users',
        'test_contest',
        'test_full_package',
        'test_problem_instance',
        'test_submission',
        'test_another_submission',
    ]

    def test_report_after_generate(self):
        self.assertTrue(self.client.login(username='test_admin'))
        contest = Contest.objects.get()
        submission = ProgramSubmission.objects.get(pk=1)
        url = reverse(
            'submission',
            kwargs={'contest_id': contest.id, 'submission_id': submission.id},
        )
        # test generate out href visibility
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '[generate out]', count=2)
        self.assertContains(response, 'Generate all', count=4)

        # test download out href visibility
        testreport = TestReport.objects.get(pk=6)
        # path to any existing file
        testreport.output_file = get_test_filename('sum-various-results.cpp')
        testreport.save()
        response = self.client.get(url)
        self.assertContains(response, '[generate out]', count=1)
        self.assertContains(response, '[download out]', count=1)

        # test filtering reports to generate user outs
        factory = RequestFactory()
        request = factory.request()
        request.contest = contest
        request.user = User.objects.get(username='test_admin')

        # test filtering and setting as processing test reports
        testreports = TestReport.objects.filter(submission_report=2)
        filtered = _testreports_to_generate_outs(request, testreports)
        # note that report with pk=6 related with test pk=3 has got
        # assigned output, so 3 lefts; 2 of them has AC status
        self.assertEqual(filtered, [2, 6, 5])
        # now all of that three are processing
        response = self.client.get(url)
        self.assertContains(response, '[processing]', count=1)
        filtered = _testreports_to_generate_outs(request, testreports)
        self.assertEqual(filtered, [])

        # test report visibility for user without permission
        self.assertTrue(self.client.login(username='test_user'))
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, '[processing]')
        self.assertNotContains(response, 'Generate all')

        # test report visibility for user with permission
        ReportActionsConfig(
            problem=submission.problem_instance.problem, can_user_generate_outs=True
        ).save()
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        # Note that 3 test are processing (by admin), what user does not see
        self.assertNotContains(response, 'Processing')
        self.assertContains(response, '[generate out]', count=1)
        # one test has assigned output (e.g. generated by system)
        self.assertContains(response, '[download out]', count=1)
        self.assertContains(response, 'Generate all', count=4)

        # clicking generate on test which is already generated but by admin
        gen_url = reverse('generate_user_output', kwargs={'testreport_id': 5})
        response = self.client.post(gen_url, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, '[generate out]')
        self.assertContains(response, '[processing]', count=1)

    def test_generate_and_download_user_permission(self):
        self.assertTrue(self.client.login(username='test_user'))
        self.client.get('/c/c/')  # 'c' becomes the current contest

        submission = ProgramSubmission.objects.get(pk=1)
        gen_url = reverse('generate_user_output', kwargs={'testreport_id': 5})
        down_one_url = reverse('download_user_output', kwargs={'testreport_id': 5})
        down_all_url = reverse(
            'download_user_output', kwargs={'submission_report_id': 2}
        )

        # post required for generate
        response = self.client.get(gen_url, follow=True)
        self.assertEqual(response.status_code, 405)
        response = self.client.post(gen_url, follow=True)
        self.assertEqual(response.status_code, 403)
        response = self.client.get(down_one_url, follow=True)
        self.assertEqual(response.status_code, 403)
        response = self.client.get(down_all_url, follow=True)
        self.assertEqual(response.status_code, 403)

        # test report visibility for user with permission
        ReportActionsConfig(
            problem=submission.problem_instance.problem, can_user_generate_outs=True
        ).save()
        response = self.client.post(gen_url, follow=True)
        self.assertEqual(response.status_code, 200)
        response = self.client.get(down_one_url, follow=True)
        self.assertEqual(response.status_code, 200)
        response = self.client.get(down_all_url, follow=True)
        self.assertEqual(response.status_code, 404)

        # test if results have not been published yet (2012-07-31)
        with fake_time(datetime(2012, 7, 29, 11, 11, tzinfo=timezone.utc)):
            response = self.client.post(gen_url, follow=True)
            self.assertEqual(response.status_code, 403)


class TestAdminInOutDownload(TestCase):
    fixtures = [
        'test_users',
        'test_contest',
        'test_full_package',
        'test_problem_instance',
        'test_submission',
    ]

    def test_report_href_visibility(self):
        self.assertTrue(self.client.login(username='test_admin'))
        contest = Contest.objects.get()
        submission = ProgramSubmission.objects.get(pk=1)
        url = reverse(
            'submission',
            kwargs={'contest_id': contest.id, 'submission_id': submission.id},
        )
        # test download in / out hrefs visibility
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        no_whitespaces_content = re.sub(r'\s*', '', response.content.decode('utf-8'))

        self.assertEqual(no_whitespaces_content.count('>out</a>'), 6)
        self.assertEqual(no_whitespaces_content.count('>in</a>'), 6)


class ContestWithJudgeInfoController(ProgrammingContestController):
    judged = False

    def submission_judged(self, submission, rejudged=False):
        super(ContestWithJudgeInfoController, self).submission_judged(
            submission, rejudged
        )
        ContestWithJudgeInfoController.judged = True


class TestRejudge(TestCase, SubmitFileMixin):
    fixtures = [
        'test_users',
        'test_contest',
        'test_full_package',
        'test_problem_instance',
        'test_submission',
        'test_extra_problem',
        'test_another_submission',
    ]

    def _set_active_tests(self, active_tests, all_tests):
        for test in all_tests:
            test.is_active = test.name in active_tests
            test.save()

    def _test_rejudge(
        self,
        submit_active_tests,
        rejudge_active_tests,
        rejudge_type,
        tests_subset,
        expected_ok,
        expected_re,
    ):
        self.assertTrue(self.client.login(username='test_user'))

        contest = Contest.objects.get()
        contest.controller_name = 'oioioi.programs.tests.ContestWithJudgeInfoController'
        contest.save()

        pi = ProblemInstance.objects.get(id=1)
        all_tests = Test.objects.filter(problem_instance=pi)

        self._set_active_tests(submit_active_tests, all_tests)

        submission = ProgramSubmission.objects.filter(id=3)
        if submission.exists():
            submission.delete()

        good_code = 'int main(void) { return 0; }'
        bad_code = 'int main(void) { return 1; }'

        ContestWithJudgeInfoController.judged = False
        self.submit_code(contest, pi, good_code)
        self.assertTrue(ContestWithJudgeInfoController.judged)

        submission = ProgramSubmission.objects.all().latest('id')

        reports = TestReport.objects.filter(
            submission_report__submission=submission, submission_report__status='ACTIVE'
        )
        for r in reports:
            self.assertIn(r.test_name, submit_active_tests)
            self.assertNotEqual(r.status, 'RE')

        submission.source_file.save('file.c', ContentFile(bad_code))

        self._set_active_tests(rejudge_active_tests, all_tests)

        ContestWithJudgeInfoController.judged = False
        submission.problem_instance.controller.judge(
            submission,
            is_rejudge=True,
            extra_args={'tests_to_judge': tests_subset, 'rejudge_type': rejudge_type},
        )
        self.assertTrue(ContestWithJudgeInfoController.judged)

        reports = TestReport.objects.filter(
            submission_report__submission=submission, submission_report__status='ACTIVE'
        )

        for r in reports:
            name = r.test_name
            status = r.status
            self.assertTrue((status == 'RE') == (name in expected_re))
            self.assertTrue((status == 'OK') == (name in expected_ok))

    def test_rejudge_full(self):
        self._test_rejudge(
            ['0', '1ocen', '1b', '3'],
            ['0', '1a', '1b', '2'],
            'FULL',
            [],
            [],
            ['0', '1a', '1b', '2'],
        )

        self._test_rejudge(['0', '1ocen'], [], 'FULL', {}, [], [])

    def test_rejudge_judged(self):
        self._test_rejudge(
            ['0', '1ocen', '1b', '3'],
            ['0', '1ocen', '1b', '3'],
            'JUDGED',
            ['0', '1a', '2', '3'],
            ['1ocen', '1b'],
            ['0', '3'],
        )

        self._test_rejudge(
            ['0', '1ocen', '1b', '3'],
            [],
            'JUDGED',
            ['0', '1a', '2', '3'],
            ['1ocen', '1b'],
            ['0', '3'],
        )

    def test_rejudge_new(self):
        self._test_rejudge(
            ['0', '1ocen', '1b', '3'],
            ['0', '1a', '1b', '2', '3'],
            'NEW',
            [],
            ['0', '1b', '3'],
            ['1a', '2'],
        )


class TestLimitsLimits(TestCase):
    fixtures = [
        'test_users',
        'test_contest',
        'test_full_package',
        'test_problem_instance',
        'test_submission',
    ]

    form_data = {
        'test_set-TOTAL_FORMS': 6,
        'test_set-INITIAL_FORMS': 6,
        'test_set-MIN_NUM_FORMS': 0,
        'test_set-MAX_NUM_FORMS': 0,
        'test_set-0-time_limit': 1000,
        'test_set-0-memory_limit': 1,
        'test_set-0-max_score': 10,
        'test_set-0-is_active': 'on',
        'test_set-0-problem_instance': 1,
        'test_set-0-id': 1,
        'test_set-1-time_limit': 1000,
        'test_set-1-memory_limit': 10,
        'test_set-1-max_score': 10,
        'test_set-1-is_active': 'on',
        'test_set-1-problem_instance': 1,
        'test_set-1-id': 4,
        'test_set-2-time_limit': 1000,
        'test_set-2-memory_limit': 10,
        'test_set-2-max_score': 10,
        'test_set-2-is_active': 'on',
        'test_set-2-problem_instance': 1,
        'test_set-2-id': 2,
        'test_set-3-time_limit': 1001,
        'test_set-3-memory_limit': 10,
        'test_set-3-max_score': 10,
        'test_set-3-is_active': 'on',
        'test_set-3-problem_instance': 1,
        'test_set-3-id': 3,
        'test_set-4-time_limit': 1000,
        'test_set-4-memory_limit': 101,
        'test_set-4-max_score': 10,
        'test_set-4-is_active': 'on',
        'test_set-4-problem_instance': 1,
        'test_set-4-id': 5,
        'test_set-5-time_limit': 1000,
        'test_set-5-memory_limit': 101,
        'test_set-5-max_score': 10,
        'test_set-5-is_active': 'on',
        'test_set-5-problem_instance': 1,
        'test_set-5-id': 6,
        'test_set-__prefix__-time-limit': '',
        'test_set-__prefix__-memory-limit': '',
        'test_set-__prefix__-max_score': 10,
        'test_set-__prefix__-is_active': 'on',
        'test_set-__prefix__-problem_instance': 3,
        'test_set-__prefix__-id': '',
        '_continue': 'Zapisz+i+kontynuuj+edycj%C4%99',
        'round': 1,
        'short_name': 'zad1',
        'submissions_limit': 10,
        'scores_reveal_config-TOTAL_FORMS': 1,
        'scores_reveal_config-INITIAL_FORMS': 0,
        'scores_reveal_config-MIN_NUM_FORMS': 0,
        'scores_reveal_config-MAX_NUM_FORMS': 1,
        'test_run_config-TOTAL_FORMS': 1,
        'test_run_config-INITIAL_FORMS': 0,
        'test_run_config-MIN_NUM_FORMS': 0,
        'test_run_config-MAX_NUM_FORMS': 1,
        'paprobleminstancedata-TOTAL_FORMS': 1,
        'paprobleminstancedata-INITIAL_FORMS': 0,
        'paprobleminstancedata-MIN_NUM_FORMS': 0,
        'paprobleminstancedata-MAX_NUM_FORMS': 1,
    }

    def edit_settings(self):
        self.assertTrue(self.client.login(username='test_admin'))
        self.client.get('/c/c/')
        return self.client.post(
            reverse(
                'oioioiadmin:contests_probleminstance_change',
                kwargs={'contest_id': 'c'},
                args=[1],
            ),
            self.form_data,
            follow=True,
        )

    @override_settings(MAX_TEST_TIME_LIMIT_PER_PROBLEM=6000)
    def test_time_limit(self):
        response = self.edit_settings()
        self.assertContains(
            response,
            "Sum of time limits for all tests is too big. It's "
            "7s, but it shouldn't exceed 6s.",
            html=True,
        )

    @override_settings(MAX_MEMORY_LIMIT_FOR_TEST=100)
    def test_memory_limit(self):
        response = self.edit_settings()
        self.assertContains(
            response,
            escape(
                "Memory limit mustn't be greater than %dKiB."
                % settings.MAX_MEMORY_LIMIT_FOR_TEST
            ),
        )


class TestCompiler(TestCase):
    fixtures = [
        'test_users',
        'test_contest',
        'test_full_package',
        'test_problem_instance',
        'test_permissions',
        'test_compilers',
    ]

    @override_settings(
        SUBMITTABLE_LANGUAGES={
            'C': {'display_name': 'C', 'type': 'main'},
            'C++': {'display_name': 'C++', 'type': 'main'},
        }
    )
    @override_settings(SUBMITTABLE_EXTENSIONS={'C': ['c'], 'C++': ['cpp', 'cc']})
    @override_settings(
        AVAILABLE_COMPILERS={
            'C': {'gcc': {'display_name': 'GNU C Compiler'}},
            'C++': {
                'gcc': {'display_name': 'GNU C Compiler'},
                'clang': {'display_name': 'Clang - LLVM compiler front end'},
            },
        }
    )
    def test_submit_view(self):
        self.assertTrue(self.client.login(username='test_user'))
        contest = Contest.objects.get()
        url = reverse('submit', kwargs={'contest_id': contest.id})
        response = self.client.get(url)
        self.assertContains(
            response, '<option value="C">C (GNU C Compiler)</option>', html=True
        )
        self.assertContains(
            response,
            '<option value="C++">C++ (Clang - LLVM compiler front end)</option>',
            html=True,
        )
        self.assertNotContains(response, 'gcc')
        self.assertNotContains(response, 'clang')

    @override_settings(
        AVAILABLE_COMPILERS={
            'C': {'gcc': {'display_name': 'gcc'}, 'clang': {'display_name': 'clang'}},
            'Python': {'python': {'display_name': 'python'}},
        }
    )
    def test_compiler_hints_view(self):
        self.assertTrue(self.client.login(username='test_admin'))

        def get_query_url(query):
            url = reverse('get_compiler_hints')
            return url + '?' + urllib.parse.urlencode({'language': query})

        response = self.client.get(get_query_url('C'), follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'gcc')
        self.assertContains(response, 'clang')
        self.assertNotContains(response, 'python')
        self.assertNotContains(response, 'g++')

        response = self.client.get(get_query_url('Python'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'python')
        self.assertNotContains(response, 'gcc')
        self.assertNotContains(response, 'clang')
        self.assertNotContains(response, 'g++')

        response = self.client.get(get_query_url('Java'))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'gcc')
        self.assertNotContains(response, 'java')
        self.assertNotContains(response, 'python')
        self.assertNotContains(response, 'clang')

    @override_settings(
        SUBMITTABLE_LANGUAGES={
            'C': {'display_name': 'C'},
            'Python': {'display_name': 'Python'},
        }
    )
    @override_settings(SUBMITTABLE_EXTENSIONS={'C': ['c'], 'Python': ['py']})
    def test_contest_admin_inline(self):
        self.assertTrue(self.client.login(username='test_admin'))

        contest = Contest.objects.get()
        url = (
            reverse('oioioiadmin:contests_contest_change', args=(quote(contest.id),))
            + '?simple=true'
        )
        response = self.client.get(url, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'C')
        self.assertContains(response, 'Python')

    @override_settings(
        SUBMITTABLE_LANGUAGES={
            'C': {'display_name': 'C'},
            'Python': {'display_name': 'Python'},
        }
    )
    @override_settings(SUBMITTABLE_EXTENSIONS={'C': ['c'], 'Python': ['py']})
    def test_contest_contest_admin_inline(self):
        self.assertTrue(self.client.login(username='test_contest_admin'))

        contest = Contest.objects.get()
        url = (
            reverse('oioioiadmin:contests_contest_change', args=(quote(contest.id),))
            + '?simple=true'
        )
        response = self.client.get(url, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'C')
        self.assertContains(response, 'Python')

    @override_settings(
        SUBMITTABLE_LANGUAGES={
            'C': {'display_name': 'C'},
            'Python': {'display_name': 'Python'},
        }
    )
    @override_settings(SUBMITTABLE_EXTENSIONS={'C': ['c'], 'Python': ['py']})
    def test_problem_admin_inline(self):
        self.assertTrue(self.client.login(username='test_admin'))

        problem = Problem.objects.get()

        self.client.get('/c/c/')  # 'c' becomes the current contest
        url = reverse('oioioiadmin:problems_problem_change', args=(problem.id,))

        response = self.client.get(url, follow=True)
        response = self.client.get(url, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'C')
        self.assertContains(response, 'Python')

    @override_settings(
        SUBMITTABLE_LANGUAGES={
            'C': {'display_name': 'C', 'type': 'main'},
            'Python': {'display_name': 'Python', 'type': 'extra'},
        }
    )
    @override_settings(SUBMITTABLE_EXTENSIONS={'C': ['c'], 'Python': ['py']})
    @override_settings(
        AVAILABLE_COMPILERS={
            'C': {'gcc': {'display_name': 'gcc'}, 'clang': {'display_name': 'clang'}},
            'Python': {'python': {'display_name': 'python'}},
        }
    )
    @override_settings(DEFAULT_COMPILERS={'C': 'gcc', 'Python': 'python'})
    def test_check_compiler_config_valid(self):
        check_compilers_config()

    @override_settings(
        SUBMITTABLE_LANGUAGES={
            'C': {'display_name': 'C'},
            'Python': {'display_name': 'Python'},
        }
    )
    @override_settings(SUBMITTABLE_EXTENSIONS={'C': ['c'], 'Python': ['py']})
    @override_settings(
        AVAILABLE_COMPILERS={
            'C': {'gcc': {'display_name': 'gcc'}, 'clang': {'display_name': 'clang'}},
            'Python': {'python': {'display_name': 'python'}},
        }
    )
    @override_settings(DEFAULT_COMPILERS={'C': 'gcc', 'Python': 'python3'})
    def test_check_compiler_config_invalid_compiler(self):
        with self.assertRaises(ImproperlyConfigured):
            check_compilers_config()

    @override_settings(
        SUBMITTABLE_LANGUAGES={
            'C': {'display_name': 'C'},
            'Python': {'display_name': 'Python'},
        }
    )
    @override_settings(SUBMITTABLE_EXTENSIONS={'C': ['c'], 'Python': ['py']})
    @override_settings(
        AVAILABLE_COMPILERS={
            'C': {'gcc': {'display_name': 'gcc'}, 'clang': {'display_name': 'clang'}}
        }
    )
    @override_settings(DEFAULT_COMPILERS={'C': 'gcc', 'Python': 'python'})
    def test_check_compiler_config_no_compiler(self):
        with self.assertRaises(ImproperlyConfigured):
            check_compilers_config()


@pytest.mark.skip(reason="Migrations have already been applied at the production")
class TestMaxScoreMigration(TestCaseMigrations):
    migrate_from = '0012_testreport_max_score'
    migrate_to = '0014_remove_testreport_test_max_score'

    def make_report(self, problem_id, contest, apps, max_score):
        if not Problem.objects.filter(id=problem_id).exists():
            Problem(id=problem_id).save()

        problem_instance_model = apps.get_model('contests', 'ProblemInstance')
        submission_model = apps.get_model('contests', 'Submission')
        submission_report_model = apps.get_model('contests', 'SubmissionReport')
        test_report_model = apps.get_model('programs', 'TestReport')

        problem_instance = problem_instance_model.objects.create(
            contest=contest,
            short_name=str(problem_id),
            contest_id=contest.id,
            problem_id=problem_id,
        )

        submission = submission_model.objects.create(problem_instance=problem_instance)
        submission_report = submission_report_model.objects.create(
            submission=submission
        )

        test_report = test_report_model.objects.create(
            submission_report=submission_report, test_max_score=max_score, time_used=1
        )

        return test_report

    def setUpBeforeMigration(self, apps):
        contest_model = apps.get_model('contests', 'Contest')

        default_contest = contest_model.objects.create(
            id=1, controller_name='oioioi.contests.controllers.ContestController'
        )
        pa_contest = contest_model.objects.create(
            id=2, controller_name='oioioi.pa.controllers.PAContestController'
        )
        acm_contest = contest_model.objects.create(
            id=3, controller_name='oioioi.acm.controllers.ACMContestController'
        )

        self.default_report_id = self.make_report(1, default_contest, apps, 100).id

        self.pa_report_id = self.make_report(2, pa_contest, apps, 100).id
        self.pa_report_zero_id = self.make_report(22, pa_contest, apps, 0).id

        self.acm_report_id = self.make_report(3, acm_contest, apps, 100).id

    def test(self):
        test_report_model = self.apps.get_model('programs', 'TestReport')

        self.assertEqual(
            test_report_model.objects.get(pk=self.default_report_id).max_score.to_int(),
            100,
        )

        self.assertEqual(
            test_report_model.objects.get(pk=self.pa_report_id).max_score.to_int(), 1
        )
        self.assertEqual(
            test_report_model.objects.get(pk=self.pa_report_zero_id).max_score.to_int(),
            0,
        )

        self.assertTrue(
            test_report_model.objects.get(pk=self.acm_report_id).max_score is None
        )


class TestReportDisplayTypes(TestCase):
    fixtures = ['admin_admin', 'test_users', 'test_report_display_test']

    def test_oi_display(self):
        self.assertTrue(self.client.login(username='test_user'))
        url = reverse('submission', kwargs={'contest_id': 'oi', 'submission_id': 7})
        response = self.client.get(url, follow=True)
        self.assertEqual(response.status_code, 200)

        self.assertContains(response, 'submission--TLE', count=2)
        self.assertContains(response, 'submission--RE', count=2)
        self.assertContains(response, 'submission--WA', count=2)

        self.assertContains(response, 'submission--OK', count=13)
        self.assertContains(response, 'submission--OK"', count=2)

        self.assertContains(response, 'submission--OK100', count=2)
        self.assertContains(response, 'submission--OK75', count=2)
        self.assertContains(response, 'submission--OK50', count=2)
        self.assertContains(response, 'submission--OK25', count=2)
        self.assertContains(response, 'submission--OK0', count=3)

    def test_acm_display(self):
        self.assertTrue(self.client.login(username='admin'))
        url = reverse('submission', kwargs={'contest_id': 'acm', 'submission_id': 9})
        response = self.client.get(url, follow=True)

        self.assertContains(response, 'submission--TLE', count=2)
        self.assertContains(response, 'submission--RE', count=3)
        self.assertContains(response, 'submission--WA', count=2)

        self.assertContains(response, 'submission--OK', count=12)
        self.assertContains(response, 'submission--OK"', count=12)

        self.assertNotContains(response, 'submission--OK100')
        self.assertNotContains(response, 'submission--OK75')
        self.assertNotContains(response, 'submission--OK50')
        self.assertNotContains(response, 'submission--OK25')
        self.assertNotContains(response, 'submission--OK0')

    def test_pa_display(self):
        self.assertTrue(self.client.login(username='test_user'))
        url = reverse('submission', kwargs={'contest_id': 'pa', 'submission_id': 11})
        response = self.client.get(url, follow=True)
        self.assertEqual(response.status_code, 200)

        self.assertContains(response, 'submission--TLE', count=2)
        self.assertContains(response, 'submission--RE', count=2)
        self.assertContains(response, 'submission--WA', count=2)

        self.assertContains(response, 'submission--OK', count=13)
        self.assertContains(response, 'submission--OK"', count=2)

        self.assertContains(response, 'submission--OK100', count=10)
        self.assertNotContains(response, 'submission--OK75')
        self.assertNotContains(response, 'submission--OK50')
        self.assertContains(response, 'submission--OK25', count=1)
        self.assertNotContains(response, 'submission--OK0')


class TestAllowedLanguages(TestCase, SubmitFileMixin):
    fixtures = [
        'test_users',
        'test_contest',
        'test_full_package',
        'test_problem_instance',
        'test_permissions',
        'test_compilers',
    ]

    @override_settings(
        SUBMITTABLE_LANGUAGES={
            'C': {'display_name': 'C'},
            'C++': {'display name': 'C++'},
            'Python': {'display_name': 'Python'},
        }
    )
    def setUp(self):
        self.problem = Problem.objects.get()
        self.problem_instance = ProblemInstance.objects.get()
        self.assertTrue(self.client.login(username='test_user'))

    def test_empty_whitelist(self):
        allowed_languages = get_allowed_languages_dict(self.problem_instance)
        self.assertIn('Python', allowed_languages)
        self.assertIn('C', allowed_languages)
        self.assertIn('C++', allowed_languages)
        self.assertNotIn('Output-only', allowed_languages)

    def test_allowed_languages_dict(self):
        ProblemAllowedLanguage.objects.create(problem=self.problem, language='C')
        ProblemAllowedLanguage.objects.create(problem=self.problem, language='C++')
        ProblemAllowedLanguage.objects.create(
            problem=self.problem, language='Output-only'
        )
        allowed_languages = get_allowed_languages_dict(self.problem_instance)
        self.assertNotIn('Python', allowed_languages)
        self.assertIn('C', allowed_languages)
        self.assertIn('C++', allowed_languages)
        self.assertIn('Output-only', allowed_languages)

    def test_disallowed_language_submit_attempt(self):
        ProblemAllowedLanguage.objects.create(problem=self.problem, language='C')
        contest = Contest.objects.get()
        response = self.submit_code(contest, self.problem_instance, prog_lang='Python')
        self.assertContains(response, 'Select a valid choice. Python is not one')
        response = self.submit_code(
            contest, self.problem_instance, 'some code', prog_lang='C'
        )
        self._assertSubmitted(contest, response)


class TestLanguageOverrideForTest(TestCase):
    fixtures = ['test_contest', 'test_full_package', 'test_problem_instance']

    def setUp(self):
        self.problem_instance = ProblemInstance.objects.get()

    def test_proper_env_override(self):
        initial_env = {
            'problem_instance_id': self.problem_instance.id,
            'language': 'cpp',
            'extra_args': {},
            'is_rejudge': False,
        }
        tests = list(Test.objects.filter(problem_instance=self.problem_instance))
        # Add override to one test.
        LanguageOverrideForTest.objects.create(
            test=tests[0], time_limit=1, memory_limit=2, language='cpp'
        )
        env_with_tests = collect_tests(initial_env)
        # Check overriden one.
        self.assertEqual(env_with_tests['tests']['0']['exec_time_limit'], 1)
        self.assertEqual(env_with_tests['tests']['0']['exec_mem_limit'], 2)
        # Check not overriden one.
        self.assertEqual(
            env_with_tests['tests']['1a']['exec_time_limit'], tests[1].time_limit
        )
        self.assertEqual(
            env_with_tests['tests']['1a']['exec_mem_limit'], tests[1].memory_limit
        )
