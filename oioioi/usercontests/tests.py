from django.conf import settings
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.test import RequestFactory
from django.test.utils import override_settings

from oioioi.base.tests import TestCase
from oioioi.contests.models import Contest
from oioioi.contests.utils import (is_contest_admin, is_contest_basicadmin,
                                   is_contest_observer)
from oioioi.programs.models import ModelProgramSubmission, Test

class TestUserContestAuthBackend(TestCase):
    fixtures = ['test_users', 'test_usercontest']

    def test_permissions_on(self):
        user = User.objects.get(pk=1001)
        contest = Contest.objects.get(pk="uc")

        self.assertFalse(user.has_perm('contests.contest_admin', contest))
        self.assertTrue(user.has_perm('contests.contest_basicadmin', contest))
        self.assertFalse(user.has_perm('contests.contest_observer', contest))

    @override_settings(AUTHENTICATION_BACKENDS=[
            backend for backend in settings.AUTHENTICATION_BACKENDS \
            if backend != 'oioioi.usercontests.auth.UserContestAuthBackend'
        ])
    def test_permissions_off(self):
        user = User.objects.get(pk=1001)
        contest = Contest.objects.get(pk="uc")

        self.assertFalse(user.has_perm('contests.contest_admin', contest))
        self.assertFalse(user.has_perm('contests.contest_basicadmin', contest))
        self.assertFalse(user.has_perm('contests.contest_observer', contest))

    @override_settings(ARCHIVE_USERCONTESTS=True)
    def test_permissions_archived(self):
        user = User.objects.get(pk=1001)
        contest = Contest.objects.get(pk="uc")

        self.assertFalse(user.has_perm('contests.contest_admin', contest))
        self.assertFalse(user.has_perm('contests.contest_basicadmin', contest))
        self.assertTrue(user.has_perm('contests.contest_observer', contest))

    def test_utils_on(self):
        user = User.objects.get(pk=1001)
        contest = Contest.objects.get(pk="uc")

        request = RequestFactory().request()
        request.contest = contest
        request.user = user

        self.assertFalse(is_contest_admin(request))
        self.assertTrue(is_contest_basicadmin(request))
        self.assertFalse(is_contest_observer(request))

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
        self.assertFalse(is_contest_observer(request))

    @override_settings(ARCHIVE_USERCONTESTS=True)
    def test_utils_archived(self):
        user = User.objects.get(pk=1001)
        contest = Contest.objects.get(pk="uc")

        request = RequestFactory().request()
        request.contest = contest
        request.user = user

        self.assertFalse(is_contest_admin(request))
        self.assertFalse(is_contest_basicadmin(request))
        self.assertTrue(is_contest_observer(request))


class TestUserContestCreationForm(TestCase):
    fixtures = ['test_users']

    def test_controller_type_hidden(self):
        self.assertTrue(self.client.login(username='test_user'))
        url = reverse('oioioiadmin:contests_contest_add')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'id_controller_name')

        self.assertTrue(self.client.login(username='test_admin'))
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
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
        self.assertEqual(response.status_code, 200)

        contest = Contest.objects.get()
        self.assertEqual(contest.controller_name,
                'oioioi.usercontests.controllers.UserContestController')

    @override_settings(ARCHIVE_USERCONTESTS=True)
    def test_archived(self):
        self.assertTrue(self.client.login(username='test_user'))
        url = reverse('oioioiadmin:contests_contest_add')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)


class TestUserContestController(TestCase):
    fixtures = ['test_users', 'test_usercontest']

    def test_can_submit(self):
        self.assertTrue(self.client.login(username='test_user2'))
        url = reverse('submit', kwargs={'contest_id': 'uc'})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'Sorry, there are no problems')

    @override_settings(ARCHIVE_USERCONTESTS=True)
    def test_cannot_submit(self):
        self.assertTrue(self.client.login(username='test_user2'))
        url = reverse('submit', kwargs={'contest_id': 'uc'})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Sorry, there are no problems')

        self.assertTrue(self.client.login(username='test_user'))
        url = reverse('submit', kwargs={'contest_id': 'uc'})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Sorry, there are no problems')


@override_settings(ARCHIVE_USERCONTESTS=True)
class TestUserContestArchived(TestCase):
    fixtures = ['test_users', 'test_usercontest', 'test_model_submissions']

    def test_can_see_problems(self):
        self.assertTrue(self.client.login(username='test_user'))
        url = reverse('problemset_my_problems')
        response = self.client.get(url, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "XYZ")

    def test_can_see_submissions(self):
        self.assertTrue(self.client.login(username='test_user'))
        self.client.get('/c/c/')

        url = reverse('show_submission_source', args=(1,))
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)

        url = reverse('show_submission_source', args=(2,))
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)

    def test_can_see_modelsolutions(self):
        self.assertTrue(self.client.login(username='test_user'))
        self.client.get('/c/c/')

        submission_id = ModelProgramSubmission.objects.first().id
        url = reverse('show_submission_source', args=(submission_id,))
        response = self.client.get(url, follow=True)
        self.assertEqual(response.status_code, 403)

    def test_can_see_tests(self):
        self.assertTrue(self.client.login(username='test_user'))
        self.client.get('/c/c/')

        test_id = Test.objects.first().id
        url = reverse('download_input_file', args=(test_id,))
        response = self.client.get(url, follow=True)
        self.assertEqual(response.status_code, 403)

        url = reverse('download_output_file', args=(test_id,))
        response = self.client.get(url, follow=True)
        self.assertEqual(response.status_code, 403)
