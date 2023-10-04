from datetime import datetime, timezone  # pylint: disable=E0611

from django.contrib.admin.utils import quote
from django.contrib.auth.models import User
from django.urls import reverse

from oioioi.balloons.models import BalloonDelivery, BalloonsDeliveryAccessData
from oioioi.base.tests import TestCase, fake_time
from oioioi.contests.models import Contest, ProblemInstance, Submission
from oioioi.participants.models import Participant
from oioioi.sinolpack.tests import get_test_filename


class TestBalloons(TestCase):
    fixtures = [
        'test_users',
        'test_contest',
        'test_full_package',
        'test_problem_instance',
    ]

    def setUp(self):
        self.contest = Contest.objects.get()
        self.c_kwargs = {'contest_id': self.contest.id}
        self.pi = ProblemInstance.objects.get()

    def test_balloons_link_and_cookie(self):
        self.assertTrue(self.client.login(username='test_user'))
        regenerate_url = reverse(
            'balloons_access_regenerate', kwargs={'contest_id': self.contest.id}
        )
        response = self.client.post(regenerate_url)
        self.assertEqual(response.status_code, 403)
        self.assertTrue(self.client.login(username='test_admin'))
        regenerate_url = reverse(
            'balloons_access_regenerate', kwargs={'contest_id': self.contest.id}
        )
        response = self.client.post(regenerate_url)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            response['Location'].endswith(
                reverse(
                    'oioioiadmin:contests_contest_change', args=[quote(self.contest.id)]
                )
            )
        )

        self.client.logout()

        access_data = BalloonsDeliveryAccessData.objects.get()
        set_cookie_url = reverse(
            'balloons_access_set_cookie',
            kwargs={
                'contest_id': self.contest.id,
                'access_key': access_data.access_key,
            },
        )
        panel_url = reverse('balloons_delivery_panel', kwargs=self.c_kwargs)
        cookie_key = 'balloons_access_' + self.contest.id
        response = self.client.get(set_cookie_url)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response['Location'].endswith(panel_url))
        self.assertTrue(cookie_key in response.cookies)
        self.assertEqual(response.cookies[cookie_key].value, access_data.access_key)

    def _generate_link_and_set_cookie(self):
        self.assertTrue(self.client.login(username='test_admin'))
        regenerate_url = reverse('balloons_access_regenerate', kwargs=self.c_kwargs)
        self.client.post(regenerate_url)
        self.client.logout()
        access_data = BalloonsDeliveryAccessData.objects.get()
        set_cookie_url = reverse(
            'balloons_access_set_cookie',
            kwargs={
                'contest_id': self.contest.id,
                'access_key': access_data.access_key,
            },
        )
        self.client.get(set_cookie_url)

    def test_balloons_access(self):
        url = reverse('balloons_delivery_panel', kwargs=self.c_kwargs)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

        self.assertTrue(self.client.login(username='test_user'))
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

        self.assertTrue(self.client.login(username='test_admin'))
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

        self._generate_link_and_set_cookie()

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def _submit_solution(self, user, source_file):
        url = reverse('submit', kwargs=self.c_kwargs)
        data = {
            'problem_instance_id': self.pi.id,
            'file': open(get_test_filename(source_file), 'rb'),
            'user': user.username,
            'kind': 'NORMAL',
        }
        return self.client.post(url, data)

    def _check_delivery(self, delivery, user, first=False):
        self.assertEqual(delivery.user, user)
        self.assertEqual(delivery.problem_instance, ProblemInstance.objects.get())
        self.assertFalse(delivery.delivered)
        self.assertEqual(delivery.first_accepted_solution, first)

    def test_balloon_request_creation(self):
        self.assertTrue(self.client.login(username='test_user'))
        user = User.objects.get(username='test_user')
        self.contest.controller_name = 'oioioi.acm.controllers.ACMContestController'
        self.contest.save()
        Participant.objects.create(user=user, contest=self.contest)

        response = self._submit_solution(user, 'sum-various-results.cpp')
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Submission.objects.count(), 1)
        self.assertEqual(BalloonDelivery.objects.count(), 0)

        response = self._submit_solution(user, 'sum-correct.cpp')
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Submission.objects.count(), 2)
        self.assertEqual(BalloonDelivery.objects.count(), 1)
        balloon_delivery = BalloonDelivery.objects.get(id=1)
        self._check_delivery(balloon_delivery, user, True)

        response = self._submit_solution(user, 'sum-correct.cpp')
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Submission.objects.count(), 3)
        self.assertEqual(BalloonDelivery.objects.count(), 1)

        self.assertTrue(self.client.login(username='test_user2'))
        user = User.objects.get(username='test_user2')
        Participant.objects.create(user=user, contest=self.contest)

        response = self._submit_solution(user, 'sum-correct.cpp')
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Submission.objects.count(), 4)
        self.assertEqual(BalloonDelivery.objects.count(), 2)
        balloon_delivery = BalloonDelivery.objects.get(id=2)
        self._check_delivery(balloon_delivery, user)

    def _check_balloon_requests(self, response, expected_number, all_number):
        response_data = response.json()
        self.assertEqual(len(response_data['new_requests']), expected_number)
        self.assertEqual(response_data['new_last_id'], all_number)
        for attr in ['id', 'team', 'problem_name', 'color', 'first_accepted']:
            for balloon_request in response_data['new_requests']:
                self.assertTrue(attr in balloon_request)

    def test_getting_new_balloon_requests(self):
        users = User.objects.all()
        requests = [
            BalloonDelivery(user=user, problem_instance=self.pi) for user in users
        ]
        BalloonDelivery.objects.bulk_create(requests)
        url = reverse('balloons_delivery_new', kwargs=self.c_kwargs)

        self._generate_link_and_set_cookie()

        response = self.client.get(url, {'last_id': -1})
        self._check_balloon_requests(response, len(users), len(users))

        for i in range(1, len(users) + 1):
            response = self.client.get(url, {'last_id': i})
            self._check_balloon_requests(response, len(users) - i, len(users))

    def test_setting_delivered_status(self):
        user = User.objects.get(username='test_user')
        BalloonDelivery.objects.create(user=user, problem_instance=self.pi)
        url = reverse('balloons_set_delivered', kwargs=self.c_kwargs)

        self._generate_link_and_set_cookie()

        response = self.client.post(url, {'id': 1, 'new_delivered': True})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(BalloonDelivery.objects.get(id=1).delivered)

        response = self.client.post(url, {'id': 1, 'new_delivered': False})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(BalloonDelivery.objects.get(id=1).delivered)

    def test_cookie_expiry_date(self):
        url = reverse('balloons_delivery_panel', kwargs=self.c_kwargs)
        with fake_time(datetime(2012, 8, 5, 0, 5, tzinfo=timezone.utc)):
            self._generate_link_and_set_cookie()
        with fake_time(datetime(2012, 8, 12, 0, 4, tzinfo=timezone.utc)):
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)
        with fake_time(datetime(2012, 8, 12, 0, 6, tzinfo=timezone.utc)):
            response = self.client.get(url)
            self.assertEqual(response.status_code, 403)
