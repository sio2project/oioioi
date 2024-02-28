from django.contrib.auth.models import User
from django.urls import reverse

from oioioi.base.tests import TestCase
from oioioi.contests.models import Contest
from oioioi.contests.tests import make_empty_contest_formset
from oioioi.contests.tests.utils import make_user_contest_admin
from oioioi.teachers.models import Teacher
from django.core.exceptions import ValidationError

from oioioi.teachers.utils import add_user_to_contest_as


def change_contest_type(contest):
    contest.controller_name = 'oioioi.teachers.controllers.TeacherContestController'
    contest.save()


class TestProblemsetPermissions(TestCase):
    fixtures = ['test_users', 'teachers']

    def test_problemset_permissions(self):
        self.assertTrue(
            self.client.login(username='test_user')
        )  # test_user is a teacher
        url_main = reverse('problemset_main')
        response = self.client.get(url_main)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Add problem')
        url_add = reverse('problemset_add_or_update')
        response = self.client.get(url_add, follow=True)
        self.assertEqual(response.status_code, 200)

        self.assertTrue(
            self.client.login(username='test_user2'))  # test_user2 is not
        response = self.client.get(url_main)
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'Add problem')
        url_add = reverse('problemset_add_or_update')
        response = self.client.get(url_add, follow=True)
        self.assertEqual(response.status_code, 403)


class TestTeacherAddContest(TestCase):
    fixtures = ['test_users', 'teachers']

    def test_teacher_add_contest(self):
        controller_name = 'oioioi.teachers.controllers.TeacherContestController'

        self.assertTrue(self.client.login(username='test_user'))
        url = reverse('oioioiadmin:contests_contest_add')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        post_data = make_empty_contest_formset()
        post_data.update(
            {
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
                'teamsconfig-0-teams_list_visible': 'NO',
            }
        )
        response = self.client.post(url, post_data, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'allow a pupil to access this contest')
        contest = Contest.objects.get()
        self.assertEqual(controller_name, contest.controller_name)


class TestSimpleUITeacherContestDashboard(TestCase):
    fixtures = ['test_users', 'test_contest']

    def test_contest_dashboard(self):
        user = User.objects.get(username='test_user')
        contest = Contest.objects.get(id='c')
        make_user_contest_admin(user, contest)

        self.assertTrue(self.client.login(username='test_user'))

        change_contest_type(contest)
        self.client.get('/c/c/')

        url = reverse('teacher_contest_dashboard')
        response = self.client.get(url)

        self.assertContains(response, "Pupils")
        self.assertContains(response, "Teachers")

        self.assertContains(response, "Test contest")

    def test_contest_dashboard_redirect(self):
        user = User.objects.get(username='test_user')
        contest = Contest.objects.get(id='c')
        make_user_contest_admin(user, contest)

        self.assertTrue(self.client.login(username='test_user'))
        response = self.client.get('/c/c/', follow=True)

        self.assertNotContains(response, "Pupils")
        self.assertNotContains(response, "Teachers")

        change_contest_type(contest)
        response = self.client.get('/c/c/', follow=True)

        self.assertContains(response, "Pupils")
        self.assertContains(response, "Teachers")

        self.assertContains(response, "Test contest")


class TestSimpleUITeacherDashboard(TestCase):
    fixtures = ['test_users', 'teachers', 'test_contest']

    def test_teacher_dashboard(self):
        self.assertTrue(self.client.login(username='test_user'))
        url = reverse('teacher_dashboard')
        response = self.client.get(url)

        self.assertContains(response, 'Teacher dashboard</h1>')
        self.assertContains(response, 'Create contest')

    def test_teacher_dashboard_permissions(self):
        self.assertTrue(self.client.login(username='test_user'))
        url = reverse('teacher_dashboard')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        self.assertTrue(self.client.login(username='test_user3'))
        url = reverse('teacher_dashboard')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

        self.assertTrue(self.client.login(username='test_admin'))
        url = reverse('teacher_dashboard')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)


class TestAdminTeacher(TestCase):
    fixtures = ['test_users', 'teachers', 'test_contest']

    def test_teacher_list(self):
        self.assertTrue(self.client.login(username='test_admin'))
        url = reverse('admin:teachers_teacher_changelist')
        response = self.client.get(url, follow=True)

        self.assertContains(response, 'Select teacher to change')

    def test_teacher_add(self):
        self.assertEqual(Teacher.objects.all().count(), 2)
        self.assertTrue(self.client.login(username='test_admin'))
        url = "/c/c" + reverse('admin:teachers_teacher_add')
        response = self.client.get(url, follow=True)
        self.assertContains(response, 'Add teacher')

        self.client.post(url, data={
            'user': 'test_user3',
            'school': 'New School',
            'is_active': 'on',
        })

        self.assertEqual(Teacher.objects.all().count(), 3)

    def test_teacher_modify(self):
        self.assertEqual(Teacher.objects.all().count(), 2)
        self.assertTrue(self.client.login(username='test_admin'))
        url = "/c/c" + reverse('oioioiadmin:teachers_teacher_change', args=('1001',))
        response = self.client.get(url, follow=True)
        self.assertContains(response, 'Change teacher')

        self.client.post(url, data={
            'user': 'test_user1',
            'school': 'New School',
            'is_active': 'on',
        })

        self.assertEqual(Teacher.objects.all().count(), 2)
        mod_teacher = Teacher.objects.get(pk=1001)
        self.assertEqual(mod_teacher.school, "New School")


class TestAddUserToContestForm(TestCase):
    fixtures = ['test_users', 'teachers', 'test_contest']

    def setUp(self):
        self.user = User.objects.get(username='test_user')
        self.c = Contest.objects.get(id='c')

        # In order to get the required URL for tests,
        # we have to first get it as a regular teacher.
        self.assertTrue(self.client.login(username='test_user'))
        add_user_to_contest_as(self.user, self.c, 'teacher')
        self.url_add_teacher = reverse(
            'teachers_add_user_to_contest',
            kwargs={'contest_id':self.c.id, 'member_type':'teacher'})
        self.url_add_pupil = reverse(
            'teachers_add_user_to_contest',
            kwargs={'contest_id':self.c.id, 'member_type':'pupil'})
        self.assertTrue(
            self.c.contestteacher_set
            .filter(teacher__user=self.user)
            .first().delete())
        self.client.logout()

    def test_add_user_to_contest_as_pupil(self):
        self.assertFalse(self.c.participant_set.filter(user=self.user))
        add_user_to_contest_as(self.user, self.c, 'pupil')
        self.assertTrue(self.c.participant_set.filter(user=self.user))

        with self.assertRaisesRegex(ValidationError, 'User is already added'):
            add_user_to_contest_as(self.user, self.c, 'pupil')
        with self.assertRaisesRegex(ValidationError, 'User is already added'):
            add_user_to_contest_as(self.user, self.c, 'teacher')

    def test_add_user_to_contest_as_teacher(self):
        self.assertFalse(
            self.c.contestteacher_set.filter(teacher__user=self.user))
        add_user_to_contest_as(self.user, self.c, 'teacher')
        self.assertTrue(
            self.c.contestteacher_set.filter(teacher__user=self.user))

        with self.assertRaisesRegex(ValidationError, 'User is already added'):
            add_user_to_contest_as(self.user, self.c, 'pupil')
        with self.assertRaisesRegex(ValidationError, 'User is already added'):
            add_user_to_contest_as(self.user, self.c, 'teacher')

    def test_add_non_teacher_as_teacher(self):
        not_teacher = User.objects.filter(is_superuser=False,
                                          teacher__isnull=True,
                                          is_active=True).first()

        with self.assertRaisesRegex(ValidationError, 'User is not a teacher'):
            add_user_to_contest_as(not_teacher, self.c, 'teacher')
        self.assertFalse(
            self.c.contestteacher_set.filter(teacher__user=self.user))
        add_user_to_contest_as(not_teacher, self.c, 'pupil')
        with self.assertRaisesRegex(ValidationError, 'User is already added'):
            add_user_to_contest_as(not_teacher, self.c, 'teacher')

    def test_http_logged_out(self):
        post_data = { 'user': 'test_user' }

        for url in [self.url_add_pupil, self.url_add_teacher]:
            response = self.client.post(url, post_data, Follow=False)
            self.assertEqual(response.status_code, 302)
            self.assertIn('/login/?next=', response['Location'])
            self.assertTrue(response['Location'].endswith(url))

            # Check if it has not added any new users.
            self.assertFalse(
                self.c.contestteacher_set.filter(teacher__user=self.user))
            self.assertFalse(
                self.c.participant_set.filter(user=self.user))

    def test_http_logged_in(self):
        self.assertTrue(self.client.login(username='test_user'))

        # Make sure 'test_user' is not a contest teacher.
        self.assertFalse(
            self.c.contestteacher_set.filter(teacher__user=self.user))
        self.assertFalse(
            self.c.participant_set.filter(user=self.user))

        def try_add():
            post_data = { 'user': 'test_user2' }  # Some other user
            for url in [self.url_add_pupil, self.url_add_teacher]:
                response = self.client.post(url, post_data, Follow=False)
                self.assertEqual(response.status_code, 403)

        try_add()

        # Retry as a contest pupil.
        add_user_to_contest_as(self.user, self.c, 'pupil')
        self.assertTrue(self.c.participant_set.filter(user=self.user))
        try_add()
