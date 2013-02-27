from datetime import datetime
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.test import TestCase
from django.utils.timezone import utc
from oioioi.base.tests import fake_time
from oioioi.contests.models import Contest, Round, RoundTimeExtension
from oioioi.problems.models import Problem
from oioioi.scoresreveal.models import ScoreRevealConfig


class TestScoresReveal(TestCase):
    fixtures = ['test_users', 'test_contest', 'test_full_package',
                'test_multiple_submissions']

    def reveal_submit(self, submission_id, check=True):
        contest = Contest.objects.get()
        kwargs = {'contest_id': contest.id, 'submission_id': submission_id}

        if check:
            url = reverse('submission', kwargs=kwargs)
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)
            self.assertIn('</i> Reveal score</a>', response.content)

        url = reverse('submission_score_reveal', kwargs=kwargs)
        response = self.client.post(url)

        if check:
            self.assertEqual(response.status_code, 302)

        return response

    def setUp(self):
        self.client.login(username='test_user')
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
        contest = Contest.objects.get()

        with fake_time(datetime(2012, 8, 8, tzinfo=utc)):
            self.reveal_submit(1)
            kwargs = {'contest_id': contest.id, 'submission_id': 1}
            response = self.client.get(reverse('submission', kwargs=kwargs))
            self.assertEqual(response.status_code, 200)
            self.assertIn('<tr><td>34</td></tr>', response.content)

    def test_disable_time(self):
        contest = Contest.objects.get()

        with fake_time(datetime(2012, 8, 9, 23, 15, tzinfo=utc)):
            kwargs = {'contest_id': contest.id, 'submission_id': 1}
            response = self.client.get(reverse('submission', kwargs=kwargs))
            self.assertEqual(response.status_code, 200)
            self.assertIn('is disabled during the last <strong>60</strong>',
                          response.content)
            response = self.reveal_submit(1, check=False)
            self.assertEqual(response.status_code, 403)

    def test_round_time_extension(self):
        user = User.objects.get(username='test_user')
        r1 = Round.objects.get()
        RoundTimeExtension(user=user, round=r1, extra_time=10).save()

        contest = Contest.objects.get()

        with fake_time(datetime(2012, 8, 9, 23, 10, tzinfo=utc)):
            kwargs = {'contest_id': contest.id, 'submission_id': 1}
            self.reveal_submit(1)

    def test_reveal_limit(self):
        contest = Contest.objects.get()

        with fake_time(datetime(2012, 8, 8, tzinfo=utc)):
            self.reveal_submit(4)
            self.reveal_submit(5)
            response = self.reveal_submit(1, check=False)
            self.assertEqual(response.status_code, 403)

            kwargs = {'contest_id': contest.id, 'submission_id': 2}
            response = self.client.get(reverse('submission', kwargs=kwargs))
            self.assertEqual(response.status_code, 200)
            self.assertIn('You have already reached the limit of the reveals.',
                          response.content)

    def test_compilation_error(self):
        contest = Contest.objects.get()

        with fake_time(datetime(2012, 8, 8, tzinfo=utc)):
            kwargs = {'contest_id': contest.id, 'submission_id': 2}
            response = self.client.get(reverse('submission', kwargs=kwargs))
            self.assertEqual(response.status_code, 200)
            self.assertNotIn('</i>Reveal score</a>', response.content)

    def test_not_scored(self):
        contest = Contest.objects.get()

        with fake_time(datetime(2012, 8, 8, tzinfo=utc)):
            kwargs = {'contest_id': contest.id, 'submission_id': 3}
            response = self.client.get(reverse('submission', kwargs=kwargs))
            self.assertEqual(response.status_code, 200)
            self.assertNotIn('has not been scored yet', response.content)

            self.reveal_submit(3)
            response = self.client.get(reverse('submission', kwargs=kwargs))
            self.assertEqual(response.status_code, 200)
            self.assertIn('has not been scored yet', response.content)
            self.assertIn('<td>&#8212;</td>', response.content)

    def test_after_round(self):
        contest = Contest.objects.get()

        with fake_time(datetime(2012, 8, 8, tzinfo=utc)):
            self.reveal_submit(4)

        with fake_time(datetime(2012, 8, 11, tzinfo=utc)):
            kwargs = {'contest_id': contest.id, 'submission_id': 4}
            response = self.client.get(reverse('submission', kwargs=kwargs))
            self.assertEqual(response.status_code, 200)
            self.assertIn('already used <strong>1</strong>/2 reveals.',
                          response.content)
            self.assertIn('<td>100</td>', response.content)

            response = self.reveal_submit(5, check=False)
            self.assertEqual(response.status_code, 403)
            kwargs = {'contest_id': contest.id, 'submission_id': 5}
            response = self.client.get(reverse('submission', kwargs=kwargs))
            self.assertNotIn('</i>Reveal score</a>', response.content)