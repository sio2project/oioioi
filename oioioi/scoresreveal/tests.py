import re
from datetime import datetime  # pylint: disable=E0611

from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.utils.timezone import utc

from oioioi.base.tests import TestCase, fake_time
from oioioi.contests.models import (Contest, Round, RoundTimeExtension,
                                    Submission)
from oioioi.problems.models import Problem
from oioioi.scoresreveal.models import ScoreRevealConfig


class TestScoresReveal(TestCase):
    fixtures = ['test_users', 'test_contest', 'test_full_package',
                'test_problem_instance', 'test_multiple_submissions']

    def reveal_submit(self, submission_id, success=True):
        contest = Contest.objects.get()
        kwargs = {'contest_id': contest.id, 'submission_id': submission_id}

        submission_url = reverse('submission', kwargs=kwargs)
        response = self.client.get(submission_url)
        self.assertEqual(response.status_code, 200)
        if success:
            self.assertIn(b'</span> Reveal score', response.content)
        else:
            self.assertNotIn(b'</span> Reveal score', response.content)

        url = reverse('submission_score_reveal', kwargs=kwargs)
        response = self.client.post(url, follow=True)
        self.assertRedirects(response, submission_url)

        self.assertEqual(response.status_code, 200)
        if success:
            self.assertIn(b'has been revealed', response.content)
        else:
            self.assertIn(b'<div class="alert alert-danger">', response.content)

        return response

    def setUp(self):
        self.client.login(username='test_user')
        self.user = User.objects.get(username='test_user')
        round = Round.objects.get()
        round.start_date = datetime(2012, 7, 31, tzinfo=utc)
        round.end_date = datetime(2012, 8, 10, tzinfo=utc)
        round.results_date = datetime(2012, 8, 12, tzinfo=utc)
        round.save()
        problem = Problem.objects.get()
        config = ScoreRevealConfig()
        config.problem = problem
        config.reveal_limit = 2
        config.disable_time = 60
        config.save()

    def test_simple_reveal(self):
        with fake_time(datetime(2012, 8, 8, tzinfo=utc)):
            response = self.reveal_submit(1)

            self.assertIn(b'34', response.content)

    def test_disable_time(self):
        contest = Contest.objects.get()

        date = datetime(2012, 8, 9, 23, 15, tzinfo=utc)
        with fake_time(date):
            submission = Submission.objects.get(pk=1)
            submission.date = date
            submission.save()

            kwargs = {'contest_id': contest.id, 'submission_id': 1}
            response = self.client.get(reverse('submission', kwargs=kwargs))
            self.assertEqual(response.status_code, 200)
            self.assertIn(b'is disabled during the last <strong>60</strong>',
                          response.content)
            self.reveal_submit(1, success=False)

    def test_round_time_extension(self):
        user = User.objects.get(username='test_user')
        r1 = Round.objects.get()
        RoundTimeExtension(user=user, round=r1, extra_time=10).save()

        with fake_time(datetime(2012, 8, 9, 23, 10, tzinfo=utc)):
            self.reveal_submit(1)

    def test_reveal_limit(self):
        with fake_time(datetime(2012, 8, 8, tzinfo=utc)):
            self.reveal_submit(4)
            self.reveal_submit(5)
            response = self.reveal_submit(1, success=False)

            self.assertIn(b'used <strong>2</strong> out of 2 reveals',
                          response.content)

    def test_compilation_error(self):
        with fake_time(datetime(2012, 8, 8, tzinfo=utc)):
            self.reveal_submit(2, success=False)

    def test_not_scored(self):
        contest = Contest.objects.get()

        with fake_time(datetime(2012, 8, 8, tzinfo=utc)):
            kwargs = {'contest_id': contest.id, 'submission_id': 3}
            response = self.client.get(reverse('submission', kwargs=kwargs))
            self.assertEqual(response.status_code, 200)
            self.assertIn(b'has not been scored yet', response.content)

            self.reveal_submit(3, success=False)

    def test_after_round(self):
        contest = Contest.objects.get()

        with fake_time(datetime(2012, 8, 8, tzinfo=utc)):
            self.reveal_submit(4)

        with fake_time(datetime(2012, 8, 11, tzinfo=utc)):
            kwargs = {'contest_id': contest.id, 'submission_id': 4}
            response = self.client.get(reverse('submission', kwargs=kwargs))
            self.assertEqual(response.status_code, 200)
            self.assertIn(b'already used <strong>1</strong> out of 2 reveals.',
                          response.content)

            no_whitespaces_response = re.sub(r'\s*', '', response.content)
            self.assertIn(b'<td>100</td>', no_whitespaces_response)
            self.reveal_submit(5, success=False)
