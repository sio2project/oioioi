from django.core.urlresolvers import reverse
from django.test import TestCase

from oioioi.contests.models import Contest


class TestProblemsetPermissions(TestCase):
    fixtures = ['test_users', 'teachers']

    def test_problemset_permissions(self):
        url_main = reverse('problemset_main')
        url_add = reverse('problemset_add_or_update')

        self.client.login(username='test_user')  # test_user is a teacher
        url_main = reverse('problemset_main')
        response = self.client.get(url_main)
        self.assertEqual(response.status_code, 200)
        self.assertIn('Add problem', response.content)
        url_add = reverse('problemset_add_or_update')
        response = self.client.get(url_add, follow=True)
        self.assertEqual(response.status_code, 200)

        self.client.login(username='test_user2')  # test_user2 is not
        response = self.client.get(url_main)
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('Add problem', response.content)
        url_add = reverse('problemset_add_or_update')
        response = self.client.get(url_add, follow=True)
        self.assertEqual(response.status_code, 403)


class TestTeacherAddContest(TestCase):
    fixtures = ['test_users', 'teachers']

    def test_teacher_add_contest(self):
        controller_name = \
                'oioioi.teachers.controllers.TeacherContestController'

        self.client.login(username='test_user')
        url = reverse('oioioiadmin:contests_contest_add')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        post_data = {
                'name': 'Teacher\'s contest',
                'id': 'tc',
                'start_date_0': '2012-02-03',
                'start_date_1': '04:05:06',
                'end_date_0': '2012-02-04',
                'end_date_1': '05:06:07',
                'results_date_0': '2012-02-05',
                'results_date_1': '06:07:08',
                'controller_name': controller_name
        }
        response = self.client.post(url, post_data, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn('allow a pupil to access this contest', response.content)
        contest = Contest.objects.get()
        self.assertEqual(controller_name, contest.controller_name)
