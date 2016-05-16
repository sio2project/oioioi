import re

from django.contrib.auth.models import User
from django.core.urlresolvers import reverse

from oioioi.base.tests import TestCase
from oioioi.contests.models import Contest, Round, Submission, \
        ContestPermission
from oioioi.questions.models import Message


class TestContestDashboard(TestCase):
    fixtures = ['test_users', 'teachers', 'test_contest', 'test_full_package',
                'test_problem_instance', 'test_messages', 'test_templates',
                'test_submission']
    compile_flags = re.M | re.S

    def test_contest_dashboard(self):

        submission = Submission.objects.all()

        c = Contest.objects.get(id='c')
        c.controller_name = \
            'oioioi.teachers.controllers.TeacherContestController'
        c.save()

        user = User.objects.get(username='test_user')
        cp = ContestPermission()
        cp.user = user
        cp.permission = 'contests.contest_admin'
        cp.contest = c
        cp.save()

        self.client.login(username='test_user')
        self.client.get('/c/c/')
        url = reverse('teacher_contest_dashboard')

        response = self.client.get(url)
        content = response.content.decode('utf-8')
        self.assertEqual(response.status_code, 200)

        self.assertIn('Recent activity', content)
        self.assertIn(c.name + '</h1>', content)

        submission = Submission.objects.get(id=1)
        problem_name = r'Sum.*yce \(zad1\)'
        problem_score = submission.score.to_int()

        regex = '.*<tr>.*' + problem_name + '.*OK.*' + str(problem_score) + \
                '.*</tr>.*'
        regex = re.compile(regex, self.compile_flags)
        self.assertTrue(regex.match(content))

        message = Message.objects.get(id=1)
        regex = '.*<tr>.*General.*' + message.topic + '.*QUESTION.*</tr>.*'
        regex = re.compile(regex, self.compile_flags)
        self.assertTrue(regex.match(content))

        regex = '.*problem__solved--low.*0 / 1.*'
        regex = re.compile(regex, self.compile_flags)
        self.assertTrue(regex.match(content))

    def test_contest_dashboard_lacking_permissions(self):
        self.client.login(username='test_user')
        self.client.get('/c/c/')
        url = reverse('teacher_contest_dashboard')

        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

    def test_contest_dashboard_no_rounds(self):
        c = Contest.objects.get(id='c')
        c.controller_name = \
            'oioioi.teachers.controllers.TeacherContestController'
        c.save()

        rounds = Round.objects.filter(contest=c)
        for rnd in rounds:
            rnd.delete()

        user = User.objects.get(username='test_user')
        cp = ContestPermission()
        cp.user = user
        cp.permission = 'contests.contest_admin'
        cp.contest = c
        cp.save()

        self.client.login(username='test_user')
        self.client.get('/c/c/')
        url = reverse('teacher_contest_dashboard')

        response = self.client.get(url)
        content = response.content.decode('utf-8')
        self.assertEqual(response.status_code, 200)

        self.assertIn('<p>There are no rounds in this contest.</p>',
                      content)
