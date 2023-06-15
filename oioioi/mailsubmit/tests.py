from datetime import datetime, timezone  # pylint: disable=E0611

from django.contrib.auth.models import User
from django.core.files.base import ContentFile
from django.urls import reverse

from oioioi.base.tests import TestCase, fake_time
from oioioi.contests.models import Contest, ProblemInstance, Round, Submission
from oioioi.mailsubmit.models import MailSubmission, MailSubmissionConfig
from oioioi.mailsubmit.utils import mail_submission_hashes
from oioioi.participants.models import Participant
from oioioi.problems.models import Problem


class MailSubmitFileMixin(object):
    def submit_file(
        self,
        contest,
        problem_instance,
        file_size=1024,
        file_name='submission.cpp',
        kind='NORMAL',
        user=None,
    ):
        url = reverse('mailsubmit', kwargs={'contest_id': contest.id})
        file = ContentFile('a' * file_size, name=file_name)
        post_data = {
            'problem_instance_id': problem_instance.id,
            'file': file,
        }
        if user:
            post_data.update(
                {
                    'kind': kind,
                    'user': user,
                }
            )
        return self.client.post(url, post_data)


class TestMailSubmission(TestCase, MailSubmitFileMixin):
    fixtures = [
        'test_users',
        'test_contest',
        'test_full_package',
        'test_problem_instance',
    ]

    def setUp(self):
        self.assertTrue(self.client.login(username='test_user'))

    def test_simple_mailsubmission(self):
        contest = Contest.objects.get()
        problem_instance = ProblemInstance.objects.get()
        problem_instance.submissions_limit = 0
        problem_instance.save()
        round = Round.objects.get()
        round.start_date = datetime(2012, 7, 31, tzinfo=timezone.utc)
        round.end_date = datetime(2012, 8, 10, tzinfo=timezone.utc)
        round.save()
        msc = MailSubmissionConfig(
            contest=contest,
            enabled=True,
            start_date=datetime(2012, 8, 12, tzinfo=timezone.utc),
            end_date=datetime(2012, 8, 14, tzinfo=timezone.utc),
        )
        msc.save()

        with fake_time(datetime(2012, 8, 11, tzinfo=timezone.utc)):
            response = self.submit_file(contest, problem_instance)
            self.assertEqual(403, response.status_code)

        self.assertEqual(MailSubmission.objects.count(), 0)

        with fake_time(datetime(2012, 8, 13, tzinfo=timezone.utc)):
            response = self.submit_file(contest, problem_instance)
            self.assertEqual(200, response.status_code)

        self.assertEqual(MailSubmission.objects.count(), 1)

        with fake_time(datetime(2012, 8, 15, tzinfo=timezone.utc)):
            response = self.submit_file(contest, problem_instance)
            self.assertEqual(403, response.status_code)

        self.assertEqual(MailSubmission.objects.count(), 1)

    def test_accepting_mailsubmissions(self):
        contest = Contest.objects.get()
        problem_instance = ProblemInstance.objects.get()
        problem_instance.submissions_limit = 0
        problem_instance.save()
        round = Round.objects.get()
        round.start_date = datetime(2012, 7, 31, tzinfo=timezone.utc)
        round.end_date = datetime(2012, 8, 10, tzinfo=timezone.utc)
        round.save()
        msc = MailSubmissionConfig(
            contest=contest,
            enabled=True,
            start_date=datetime(2012, 8, 12, tzinfo=timezone.utc),
            end_date=datetime(2012, 8, 14, tzinfo=timezone.utc),
        )
        msc.save()

        with fake_time(datetime(2012, 8, 13, tzinfo=timezone.utc)):
            response = self.submit_file(contest, problem_instance)
            self.assertEqual(200, response.status_code)

        self.assertEqual(MailSubmission.objects.count(), 1)
        ms = MailSubmission.objects.get()
        _ms_source_hash, ms_submission_hash = mail_submission_hashes(ms)

        self.assertEqual(Submission.objects.count(), 0)

        url = reverse(
            'accept_mailsubmission_default', kwargs={'contest_id': contest.id}
        )
        valid_post_data = {
            'mailsubmission_id': ms.id,
            'submission_hash': ms_submission_hash,
        }
        invalid_post_data = {'mailsubmission_id': ms.id, 'submission_hash': 'ABCDE'}

        response = self.client.post(url, valid_post_data)
        self.assertEqual(403, response.status_code)
        self.assertEqual(Submission.objects.count(), 0)

        self.assertTrue(self.client.login(username='test_admin'))
        response = self.client.post(url, invalid_post_data)
        self.assertEqual(200, response.status_code)
        self.assertContains(response, 'Invalid confirmation code')
        self.assertEqual(Submission.objects.count(), 0)

        response = self.client.post(url, valid_post_data, follow=True)
        self.assertEqual(200, response.status_code)
        self.assertEqual(Submission.objects.count(), 1)
        response = self.client.post(url, valid_post_data, follow=True)
        self.assertEqual(200, response.status_code)
        self.assertContains(response, 'already accepted')
        ms = MailSubmission.objects.get()
        self.assertEqual(ms.accepted_by, User.objects.get(username='test_admin'))

    def test_mailsubmit_permissions(self):
        contest = Contest.objects.get()
        contest.controller_name = (
            'oioioi.participants.tests.ParticipantsContestController'
        )
        contest.save()

        problem_instance = ProblemInstance.objects.get()
        problem_instance.submissions_limit = 0
        problem_instance.save()
        round = Round.objects.get()
        round.start_date = datetime(2012, 7, 31, tzinfo=timezone.utc)
        round.end_date = datetime(2012, 8, 10, tzinfo=timezone.utc)
        round.save()
        msc = MailSubmissionConfig(
            contest=contest,
            enabled=True,
            start_date=datetime(2012, 8, 12, tzinfo=timezone.utc),
            end_date=datetime(2012, 8, 14, tzinfo=timezone.utc),
        )
        msc.save()

        user = User.objects.get(username='test_user')
        p = Participant(contest=contest, user=user, status='BANNED')
        p.save()

        with fake_time(datetime(2012, 8, 13, 0, 5, tzinfo=timezone.utc)):
            self.assertTrue(self.client.login(username='test_user2'))
            response = self.submit_file(contest, problem_instance)
            self.assertEqual(403, response.status_code)

            self.assertTrue(self.client.login(username='test_user'))
            response = self.submit_file(contest, problem_instance)
            self.assertEqual(403, response.status_code)

            p.status = 'ACTIVE'
            p.save()

            self.assertEqual(MailSubmission.objects.count(), 0)

            self.assertTrue(self.client.login(username='test_user'))
            response = self.submit_file(contest, problem_instance)
            self.assertEqual(200, response.status_code)

            self.assertEqual(MailSubmission.objects.count(), 1)

    def test_mailsubmissions_list(self):
        c1 = Contest(
            id='contest1',
            name='Contest1',
            controller_name='oioioi.participants.'
            'tests.ParticipantsContestController',
        )
        c1.save()
        c2 = Contest(
            id='contest2',
            name='Contest2',
            controller_name='oioioi.participants.'
            'tests.ParticipantsContestController',
        )
        c2.save()
        p = Problem.objects.get()
        pi1 = ProblemInstance(contest=c1, problem=p, short_name='problem_instance1')
        pi1.save()
        pi2 = ProblemInstance(contest=c2, problem=p, short_name='problem_instance2')
        pi2.save()
        u = User.objects.get(username='test_user')
        f = ContentFile(b'aaa', name='bbbb.cpp')
        ms1 = MailSubmission(problem_instance=pi1, user=u)
        ms1.source_file.save(f.name, f)
        ms1.save()
        ms2 = MailSubmission(problem_instance=pi2, user=u)
        ms2.source_file.save(f.name, f)
        ms2.save()

        self.assertTrue(self.client.login(username='test_admin'))
        url = reverse(
            'oioioiadmin:mailsubmit_mailsubmission_changelist',
            kwargs={'contest_id': 'contest1'},
        )
        response = self.client.get(url)
        self.assertContains(response, 'problem_instance1')
        self.assertNotContains(response, 'problem_instance2')
        url = reverse(
            'oioioiadmin:mailsubmit_mailsubmission_changelist',
            kwargs={'contest_id': 'contest2'},
        )
        response = self.client.get(url)
        self.assertContains(response, 'problem_instance2')
        self.assertNotContains(response, 'problem_instance1')
