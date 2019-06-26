from django.conf import settings
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.test import RequestFactory
from django.test.utils import override_settings

from oioioi.base.tests import TestCase
from oioioi.contests.models import Contest
from oioioi.contests.utils import is_contest_admin, is_contest_basicadmin


class TestUserContestAuthBackend(TestCase):
    fixtures = ['test_users', 'test_usercontest']

    def test_permissions_on(self):
        user = User.objects.get(pk=1001)
        contest = Contest.objects.get(pk="uc")

        self.assertFalse(user.has_perm('contests.contest_admin', contest))
        self.assertTrue(user.has_perm('contests.contest_basicadmin', contest))

    @override_settings(AUTHENTICATION_BACKENDS=[
            backend for backend in settings.AUTHENTICATION_BACKENDS \
            if backend != 'oioioi.usercontests.auth.UserContestAuthBackend'
        ])
    def test_permissions_off(self):
        user = User.objects.get(pk=1001)
        contest = Contest.objects.get(pk="uc")

        self.assertFalse(user.has_perm('contests.contest_admin', contest))
        self.assertFalse(user.has_perm('contests.contest_basicadmin', contest))

    def test_utils_on(self):
        user = User.objects.get(pk=1001)
        contest = Contest.objects.get(pk="uc")

        request = RequestFactory().request()
        request.contest = contest
        request.user = user

        self.assertFalse(is_contest_admin(request))
        self.assertTrue(is_contest_basicadmin(request))

    @override_settings(AUTHENTICATION_BACKENDS=[
            backend for backend in settings.AUTHENTICATION_BACKENDS \
            if backend != 'oioioi.usercontests.auth.UserContestAuthBackend'
        ])
    def test_utils_off(self):
        user = User.objects.get(pk=1001)
        contest = Contest.objects.get(pk="uc")

        request = RequestFactory().request()
        request.contest = contest
        request.user = user

        self.assertFalse(is_contest_admin(request))
        self.assertFalse(is_contest_basicadmin(request))


class TestUserContestCreationForm(TestCase):
    fixtures = ['test_users']

    def test_controller_type_hidden(self):
        self.assertTrue(self.client.login(username='test_user'))
        url = reverse('oioioiadmin:contests_contest_add')
        response = self.client.get(url)
        self.assertEquals(response.status_code, 200)
        self.assertNotContains(response, 'id_controller_name')

        self.assertTrue(self.client.login(username='test_admin'))
        response = self.client.get(url)
        self.assertEquals(response.status_code, 200)
        self.assertContains(response, 'id_controller_name')

    def test_contest_creation(self):
        self.assertTrue(self.client.login(username='test_user'))
        url = reverse('oioioiadmin:contests_contest_add')

        data = {
            'name': 'test usercontest',
            'id': 'test-usercontest',
            'default_submissions_limit': 0,
            'start_date_0': '2077-04-19',
            'start_date_1': '00:00:00',
            "round_set-TOTAL_FORMS": 0,
            "round_set-INITIAL_FORMS": 0,
            "round_set-MIN_NUM_FORMS": 0,
            "round_set-MAX_NUM_FORMS": 1000,
            "c_attachments-TOTAL_FORMS": 0,
            "c_attachments-INITIAL_FORMS": 0,
            "c_attachments-MIN_NUM_FORMS": 0,
            "c_attachments-MAX_NUM_FORMS": 1000,
            "contestlink_set-TOTAL_FORMS": 0,
            "contestlink_set-INITIAL_FORMS": 0,
            "contestlink_set-MIN_NUM_FORMS": 0,
            "contestlink_set-MAX_NUM_FORMS": 1000,
            "exclusivenessconfig_set-TOTAL_FORMS": 0,
            "exclusivenessconfig_set-INITIAL_FORMS": 0,
            "exclusivenessconfig_set-MAX_NUM_FORMS": 0,
            "contesticon_set-TOTAL_FORMS": 0,
            "contesticon_set-INITIAL_FORMS": 0,
            "contesticon_set-MIN_NUM_FORMS": 0,
            "contesticon_set-MAX_NUM_FORMS": 1000,
            "contestlogo-TOTAL_FORMS": 1,
            "contestlogo-INITIAL_FORMS": 0,
            "contestlogo-MIN_NUM_FORMS": 0,
            "contestlogo-MAX_NUM_FORMS": 1,
        }
        response = self.client.post(url, data, follow=True)
        self.assertEquals(response.status_code, 200)

        contest = Contest.objects.get()
        self.assertEquals(contest.controller_name,
                'oioioi.usercontests.controllers.UserContestController')
