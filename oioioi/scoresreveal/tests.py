import re
from datetime import datetime, timezone  # pylint: disable=E0611

from django.contrib.auth.models import User
from django.urls import reverse

from oioioi.base.tests import TestCase, fake_time
from oioioi.contests.models import (
    Contest,
    ProblemInstance,
    Round,
    RoundTimeExtension,
    Submission,
)
from oioioi.scoresreveal.models import ScoreRevealConfig
from oioioi.quizzes.models import QuizSubmission


class TestScoresManualReveal(TestCase):
    fixtures = [
        'test_users',
        'test_contest',
        'test_full_package',
        'test_problem_instance',
        'test_multiple_submissions',
    ]

    def reveal_submit(self, submission_id, success=True):
        contest = Contest.objects.get()
        kwargs = {'contest_id': contest.id, 'submission_id': submission_id}

        submission_url = reverse('submission', kwargs=kwargs)
        response = self.client.get(submission_url)
        self.assertEqual(response.status_code, 200)
        if success:
            self.assertContains(response, '</i> Reveal score')
        else:
            self.assertNotContains(response, '</i> Reveal score')

        url = reverse('submission_score_reveal', kwargs=kwargs)
        response = self.client.post(url, follow=True)
        self.assertRedirects(response, submission_url)

        self.assertEqual(response.status_code, 200)
        if success:
            self.assertContains(response, 'has been revealed')
        else:
            self.assertContains(response, '<div class="alert alert-danger">')

        return response

    def setUp(self):
        self.assertTrue(self.client.login(username='test_user'))
        self.user = User.objects.get(username='test_user')
        round = Round.objects.get()
        round.start_date = datetime(2012, 7, 31, tzinfo=timezone.utc)
        round.end_date = datetime(2012, 8, 10, tzinfo=timezone.utc)
        round.results_date = datetime(2012, 8, 12, tzinfo=timezone.utc)
        round.save()
        problem_instance = ProblemInstance.objects.get()
        config = ScoreRevealConfig()
        config.problem_instance = problem_instance
        config.reveal_limit = 2
        config.disable_time = 60
        config.save()

    def test_simple_reveal(self):
        with fake_time(datetime(2012, 8, 8, tzinfo=timezone.utc)):
            response = self.reveal_submit(1)

            self.assertContains(response, '34')

    def test_disable_time(self):
        contest = Contest.objects.get()

        date = datetime(2012, 8, 9, 23, 15, tzinfo=timezone.utc)
        with fake_time(date):
            submission = Submission.objects.get(pk=1)
            submission.date = date
            submission.save()

            kwargs = {'contest_id': contest.id, 'submission_id': 1}
            response = self.client.get(reverse('submission', kwargs=kwargs))
            self.assertEqual(response.status_code, 200)
            self.assertContains(
                response, 'is disabled during the last <strong>60</strong>'
            )
            self.reveal_submit(1, success=False)

    def test_round_time_extension(self):
        user = User.objects.get(username='test_user')
        r1 = Round.objects.get()
        RoundTimeExtension(user=user, round=r1, extra_time=10).save()

        with fake_time(datetime(2012, 8, 9, 23, 10, tzinfo=timezone.utc)):
            self.reveal_submit(1)

    def test_reveal_limit(self):
        with fake_time(datetime(2012, 8, 8, tzinfo=timezone.utc)):
            self.reveal_submit(4)
            self.reveal_submit(5)
            response = self.reveal_submit(1, success=False)

            self.assertContains(response, 'used <strong>2</strong> out of 2 reveals')

    def test_compilation_error(self):
        with fake_time(datetime(2012, 8, 8, tzinfo=timezone.utc)):
            self.reveal_submit(2, success=False)

    def test_not_scored(self):
        contest = Contest.objects.get()

        with fake_time(datetime(2012, 8, 8, tzinfo=timezone.utc)):
            kwargs = {'contest_id': contest.id, 'submission_id': 3}
            response = self.client.get(reverse('submission', kwargs=kwargs))
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, 'has not been scored yet')

            self.reveal_submit(3, success=False)

    def test_after_round(self):
        contest = Contest.objects.get()

        with fake_time(datetime(2012, 8, 8, tzinfo=timezone.utc)):
            self.reveal_submit(4)

        with fake_time(datetime(2012, 8, 11, tzinfo=timezone.utc)):
            kwargs = {'contest_id': contest.id, 'submission_id': 4}
            response = self.client.get(reverse('submission', kwargs=kwargs))
            self.assertEqual(response.status_code, 200)
            self.assertContains(
                response, 'already used <strong>1</strong> out of 2 reveals.'
            )

            no_whitespaces_response = re.sub(
                r'\s*', '', response.content.decode('utf-8')
            )
            self.assertIn('<td>100</td>', no_whitespaces_response)
            self.reveal_submit(5, success=False)


class TestScoresAutoReveal(TestCase):
    fixtures = [
        'test_users',
        'test_contest',
        'test_full_package',
        'test_problem_instance',
        'test_multiple_submissions',
    ]

    def setUp(self):
        self.assertTrue(self.client.login(username='test_user'))
        self.user = User.objects.get(username='test_user')
        round = Round.objects.get()
        round.start_date = datetime(2012, 7, 31, tzinfo=timezone.utc)
        round.end_date = datetime(2012, 8, 10, tzinfo=timezone.utc)
        round.results_date = datetime(2012, 8, 12, tzinfo=timezone.utc)
        round.save()
        problem_instance = ProblemInstance.objects.get()
        config = ScoreRevealConfig()
        config.problem_instance = problem_instance
        config.reveal_limit = None
        config.disable_time = 60
        config.save()

    def get_submission_page(self, submission_id):
        contest = Contest.objects.get()
        kwargs = {'contest_id': contest.id, 'submission_id': submission_id}

        submission_url = reverse('submission', kwargs=kwargs)
        response = self.client.get(submission_url)
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, '</i> Reveal score')

        return response

    def no_whitespaces(self, response):
        return re.sub(r'\s*', '', response.content.decode('utf-8'))

    def test_simple_reveal(self):
        with fake_time(datetime(2012, 8, 8, tzinfo=timezone.utc)):
            self.assertIn(
                '<td>34</td>', self.no_whitespaces(self.get_submission_page(1))
            )
            self.assertIn(
                '<td>100</td>', self.no_whitespaces(self.get_submission_page(4))
            )
            self.assertIn(
                '<td>90</td>', self.no_whitespaces(self.get_submission_page(5))
            )

    def test_disable_time(self):
        date = datetime(2012, 8, 9, 23, 15, tzinfo=timezone.utc)
        submission = Submission.objects.get(pk=1)
        submission.date = date
        submission.save()

        with fake_time(date):
            response = self.get_submission_page(1)
            self.assertNotIn('<td>34</td>', self.no_whitespaces(response))
            self.assertContains(
                self.get_submission_page(1),
                'is disabled during the last <strong>60</strong>',
            )

    def test_round_time_extension(self):
        user = User.objects.get(username='test_user')
        r1 = Round.objects.get()
        RoundTimeExtension(user=user, round=r1, extra_time=10).save()

        date = datetime(2012, 8, 9, 23, 10, tzinfo=timezone.utc)
        with fake_time(date):
            submission = Submission.objects.get(pk=1)
            submission.date = date
            submission.save()
            self.assertContains(self.get_submission_page(1), '34')

    def test_compilation_error(self):
        with fake_time(datetime(2012, 8, 8, tzinfo=timezone.utc)):
            self.assertContains(
                self.get_submission_page(2),
                'You cannot reveal the score of the submission with status',
            )

    def test_not_scored(self):
        with fake_time(datetime(2012, 8, 8, tzinfo=timezone.utc)):
            self.assertContains(self.get_submission_page(3), 'has not been scored yet')

    def test_after_round(self):
        with fake_time(datetime(2012, 8, 10, 10, tzinfo=timezone.utc)):
            response = self.get_submission_page(4)
            no_whitespaces_response = re.sub(
                r'\s*', '', response.content.decode('utf-8')
            )
            self.assertIn('<td>100</td>', no_whitespaces_response)


class TestRevealQuiz(TestCase):
    fixtures = [
        'test_users',
        'test_contest',
        'test_quiz_problem',
        'test_problem_instance',
        'test_quiz_submission',
    ]

    def check_reports(self, kwargs):
        submission_url = reverse('submission', kwargs=kwargs)
        response = self.client.get(submission_url)
        self.assertEqual(response.status_code, 200)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '27 / 27', count=1)
        self.assertContains(response, '0 / 27', count=1)
        expected_score = 50
        self.assertContains(response, '<td>{}</td>'.format(expected_score), html=True)

        url = reverse('submission_score_reveal', kwargs=kwargs)
        response = self.client.post(url, follow=True)
        self.assertRedirects(response, submission_url)

        self.assertEqual(response.status_code, 200)

    def setUp(self):
        self.assertTrue(self.client.login(username='test_user'))
        problem_instance = ProblemInstance.objects.get()
        config = ScoreRevealConfig()
        config.problem_instance = problem_instance
        config.reveal_limit = None
        config.disable_time = 60
        config.save()

    def test_first_submission(self):
        contest = Contest.objects.get()
        submission = QuizSubmission.objects.get(pk=1)
        kwargs = {'contest_id': contest.id, 'submission_id': submission.id}
        self.check_reports(kwargs)

    def test_second_submisson(self):
        submission = QuizSubmission.objects.get(pk=2)
        kwargs = {
            'contest_id': submission.problem_instance.contest.id,
            'submission_id': submission.id,
        }
        self.check_reports(kwargs)
