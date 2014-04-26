import json

from django.test import TestCase
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse

from oioioi.contests.models import Contest
from oioioi.participants.models import Participant
from oioioi.pa.models import PARegistration


class TestPARegistration(TestCase):
    fixtures = ['test_users', 'test_contest']

    def setUp(self):
        contest = Contest.objects.get()
        contest.controller_name = \
                'oioioi.pa.controllers.PAContestController'
        contest.save()
        self.reg_data = {
            'address': 'The Castle',
            'postal_code': '31-337',
            'city': 'Camelot',
            'phone': '000-000-000',
            't_shirt_size': 'L',
            'job': 'AS',
            'job_name': 'WSRH',
            'terms_accepted': 'y',
        }

    def test_participants_registration(self):
        contest = Contest.objects.get()
        user = User.objects.get(username='test_user')
        url = reverse('participants_register',
                      kwargs={'contest_id': contest.id})
        self.client.login(username='test_user')
        response = self.client.get(url)
        self.assertContains(response, 'Postal code')

        user.first_name = 'Sir Lancelot'
        user.last_name = 'du Lac'
        user.save()

        response = self.client.post(url, self.reg_data)
        self.assertEquals(302, response.status_code)

        registration = PARegistration.objects.get(participant__user=user)
        self.assertEquals(registration.address, self.reg_data['address'])

    def test_contest_info(self):
        contest = Contest.objects.get()
        user = User.objects.get(username='test_user')
        p = Participant(contest=contest, user=user)
        p.save()
        PARegistration(participant_id=p.id, **self.reg_data).save()
        url = reverse('contest_info', kwargs={'contest_id': contest.id})
        data = json.loads(self.client.get(url).content)
        self.assertEquals(data['users_count'], 1)
