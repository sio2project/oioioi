from datetime import datetime
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.test import RequestFactory
from pytz import utc
from oioioi.base.tests import TestCase, fake_time
from oioioi.contests.models import Contest, Submission
from oioioi.disqualification.models import Disqualification


def _disqualify_contestwide():
    disqualification = Disqualification(
        user=User.objects.get(username='test_user'),
        contest=Contest.objects.get(),
        title="I cannot tell!",
        content="Suffice to say, is one of the words "
                "the Knights of Ni cannot hear!")
    disqualification.save()


class TestContestController(TestCase):
    fixtures = ['test_contest', 'test_users', 'test_submission',
        'test_full_package', 'test_problem_instance',
        'test_another_submission', 'test_submission_disqualification']

    def _get_fake_request(self, user, contest):
        def wrapped():
            fake_request = RequestFactory().request()
            fake_request.user = user
            fake_request.contest = contest
            fake_request.timestamp = datetime(2013, 1, 1, tzinfo=utc)
            return fake_request
        return wrapped

    def test_disqualified(self):
        user = User.objects.get(username='test_user')
        contest = Contest.objects.get()
        controller = contest.controller
        submission = Submission.objects.get(id=1)
        submission_ok = Submission.objects.get(id=2)
        fake_request = self._get_fake_request(user, contest)

        self.assertTrue(controller.is_submission_disqualified(submission))
        self.assertFalse(controller.is_submission_disqualified(submission_ok))
        self.assertTrue(controller.has_disqualification_history(submission))
        self.assertFalse(controller.has_disqualification_history(
            submission_ok))
        self.assertTrue(controller.is_any_submission_to_problem_disqualified(
            user, submission.problem_instance))
        self.assertTrue(controller.is_user_disqualified(fake_request(), user))
        self.assertFalse(controller.results_visible(fake_request(),
                                                    submission))

        # submission_ok is a submission to the same problem
        self.assertFalse(controller.results_visible(
            fake_request(), submission_ok))
        self.assertNotIn(user, controller.exclude_disqualified_users(
            fake_request(), User.objects.all()))

        other_contest = Contest(name='finding_another_shrubbery',
                                controller_name=contest.controller_name,
                                creation_date=contest.creation_date)
        other_contest.save()
        other_fake_request = self._get_fake_request(user, other_contest)
        self.assertFalse(other_contest.controller.is_user_disqualified(
            other_fake_request(), user))

    def test_not_disqualified(self):
        user = User.objects.get(username='test_user2')
        contest = Contest.objects.get()
        controller = contest.controller
        submission = Submission.objects.get(id=2)
        submission.user = user
        submission.save()
        fake_request = self._get_fake_request(user, contest)

        self.assertFalse(controller.is_submission_disqualified(submission))
        self.assertFalse(controller.has_disqualification_history(submission))
        self.assertFalse(controller.is_any_submission_to_problem_disqualified(
            user, submission.problem_instance))
        self.assertFalse(controller.is_user_disqualified(fake_request(), user))
        self.assertTrue(controller.results_visible(fake_request(), submission))
        self.assertIn(user, controller.exclude_disqualified_users(
            fake_request(), User.objects.all()))

    def test_disqualified_contestwide(self):
        Disqualification.objects.all().delete()
        _disqualify_contestwide()
        user = User.objects.get(username='test_user')
        contest = Contest.objects.get()
        controller = contest.controller
        submission = Submission.objects.get(id=1)
        fake_request = self._get_fake_request(user, contest)

        self.assertFalse(controller.is_submission_disqualified(submission))
        self.assertFalse(controller.has_disqualification_history(submission))
        self.assertFalse(controller.is_any_submission_to_problem_disqualified(
            user, submission.problem_instance))
        self.assertTrue(controller.is_user_disqualified(fake_request(), user))
        self.assertTrue(controller.results_visible(fake_request(), submission))
        self.assertNotIn(user, controller.exclude_disqualified_users(
            fake_request(), User.objects.all()))


class TestViews(TestCase):
    fixtures = ['test_contest', 'test_users', 'test_full_package',
        'test_problem_instance', 'test_submission', 'test_another_submission',
        'test_submission_disqualification']

    def setUp(self):
        self.contest_kwargs = {'contest_id': Contest.objects.get().id}

    def _assert_disqualification_box(self, response_callback):
        with fake_time(datetime(2015, 1, 1, tzinfo=utc)):
            response = response_callback()
            self.assertContains(response, "Disqualification")
            self.assertContains(response, "Ni in code")
            self.assertContains(response, "ninininini")
            self.assertNotContains(response, "Score")
            self.assertNotContains(response, '>34</td>')
            self.assertNotContains(response, '>42</td>')

        _disqualify_contestwide()
        with fake_time(datetime(2015, 1, 1, tzinfo=utc)):
            response = response_callback()
            self.assertContains(response, "Disqualification")
            self.assertContains(response, "Ni in code")
            self.assertContains(response, "I cannot tell")
            self.assertContains(response, "Knights of Ni")
            self.assertNotContains(response, '>34</td>')
            self.assertNotContains(response, '>42</td>')

        Disqualification.objects.filter(submission__isnull=False).delete()
        with fake_time(datetime(2015, 1, 1, tzinfo=utc)):
            response = response_callback()
            self.assertContains(response, "Disqualification")
            self.assertNotContains(response, "Ni in code")
            self.assertContains(response, "I cannot tell")
            self.assertContains(response, "Knights of Ni")
            # Even disqualified users can see their score
            self.assertContains(response, '>34</td>')

    def test_dashboard(self):
        self.client.login(username='test_user')
        response_cb = lambda: self.client.get(reverse('contest_dashboard',
                                           kwargs=self.contest_kwargs),
                                   follow=True)
        self._assert_disqualification_box(response_cb)

    def test_my_submissions(self):
        self.client.login(username='test_user')
        response_cb = lambda: self.client.get(reverse('my_submissions',
            kwargs=self.contest_kwargs))

        self._assert_disqualification_box(response_cb)

    def test_submission(self):
        self.client.login(username='test_user')
        submission = Submission.objects.get(id=1)

        with fake_time(datetime(2015, 1, 1, tzinfo=utc)):
            response = self.client.get(reverse('submission',
                kwargs={'submission_id': submission.id,
                        'contest_id': Contest.objects.get().id}))
            self.assertContains(response, "Disqualification")
            self.assertContains(response, "Ni in code")
            self.assertContains(response, "ninininini")
            self.assertNotContains(response, '>34</td>')

        # Not disqualified submission
        submission = Submission.objects.get(id=2)
        with fake_time(datetime(2015, 1, 1, tzinfo=utc)):
            response = self.client.get(reverse('submission',
                kwargs={'submission_id': submission.id,
                        'contest_id': Contest.objects.get().id}))
            self.assertNotContains(response, "Disqualification")
            self.assertNotContains(response, "Ni in code")
            self.assertNotContains(response, "ninininini")
            self.assertNotContains(response, '>42</td>')
            self.assertContains(response, 'Submission 2')

    def test_ranking(self):
        contest = Contest.objects.get()
        url = reverse('default_ranking', kwargs={'contest_id': contest.id})

        self.client.login(username='test_admin')
        with fake_time(datetime(2015, 1, 1, tzinfo=utc)):
            response = self.client.get(url)
            self.assertContains(response, "Test User")
            self.assertContains(response, "disqualified")

        self.client.login(username='test_user')
        with fake_time(datetime(2015, 1, 1, tzinfo=utc)):
            response = self.client.get(url)
            self.assertNotContains(response, "Test User")

    def test_ranking_csv(self):
        contest = Contest.objects.get()
        url = reverse('ranking_csv', kwargs={'contest_id': contest.id,
                                             'key': 'c'})

        self.client.login(username='test_admin')
        with fake_time(datetime(2015, 1, 1, tzinfo=utc)):
            response = self.client.get(url)
            self.assertContains(response, "Test")
            self.assertContains(response, "Disqualified")
            self.assertContains(response, "Yes")
            self.assertContains(response, "34")
