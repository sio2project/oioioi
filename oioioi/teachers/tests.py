from django.core.urlresolvers import reverse

from oioioi.base.tests import TestCase
from oioioi.contests.models import Contest
from oioioi.contests.tests import make_empty_contest_formset


class TestProblemsetPermissions(TestCase):
    fixtures = ['test_users', 'teachers']

    def test_problemset_permissions(self):
        self.assertTrue(self.client.login(username='test_user'))  # test_user is a teacher
        url_main = reverse('problemset_main')
        response = self.client.get(url_main)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Add problem')
        url_add = reverse('problemset_add_or_update')
        response = self.client.get(url_add, follow=True)
        self.assertEqual(response.status_code, 200)

        self.assertTrue(self.client.login(username='test_user2'))  # test_user2 is not
        response = self.client.get(url_main)
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'Add problem')
        url_add = reverse('problemset_add_or_update')
        response = self.client.get(url_add, follow=True)
        self.assertEqual(response.status_code, 403)


class TestTeacherAddContest(TestCase):
    fixtures = ['test_users', 'teachers']

    def test_teacher_add_contest(self):
        controller_name = \
                'oioioi.teachers.controllers.TeacherContestController'

        self.assertTrue(self.client.login(username='test_user'))
        url = reverse('oioioiadmin:contests_contest_add')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        post_data = make_empty_contest_formset()
        post_data.update({
                'name': 'Teacher\'s contest',
                'id': 'tc',
                'start_date_0': '2012-02-03',
                'start_date_1': '04:05:06',
                'end_date_0': '2012-02-04',
                'end_date_1': '05:06:07',
                'results_date_0': '2012-02-05',
                'results_date_1': '06:07:08',
                'controller_name': controller_name,
                'problemstatementconfig-0-visible': 'AUTO',
                'teamsconfig-0-max_team_size': 3,
                'teamsconfig-0-teams_list_visible': 'NO'
        })
        response = self.client.post(url, post_data, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'allow a pupil to access this contest')
        contest = Contest.objects.get()
        self.assertEqual(controller_name, contest.controller_name)
