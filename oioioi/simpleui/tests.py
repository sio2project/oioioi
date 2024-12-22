import re
from datetime import datetime, timezone  # pylint: disable=E0611

from django.conf import settings
from django.contrib.auth.models import User
from django.test.utils import override_settings
from django.urls import reverse
from django.utils import timezone as django_timezone

from oioioi.base.tests import TestCase, fake_timezone_now
from oioioi.contests.controllers import ContestControllerContext
from oioioi.contests.models import (
    Contest,
    ContestPermission,
    ProblemInstance,
    Round,
    Submission,
)
from oioioi.contests.tests.utils import make_user_contest_admin
from oioioi.programs.models import Test
from oioioi.questions.models import Message
from oioioi.simpleui.views import get_round_context


def change_contest_type(contest):
    contest.controller_name = 'oioioi.contests.tests.PrivateContestController'
    contest.save()

def get_contest_problem_instances():
    contest = Contest.objects.get(pk='c')
    request = ContestControllerContext(contest, django_timezone.now(), True)
    round = Round.objects.filter(contest=contest).first()
    return get_round_context(request, round.pk)['selected_round']['problem_instances']


class TestContestDashboard(TestCase):
    fixtures = [
        'test_users',
        'test_contest',
        'test_full_package',
        'test_problem_instance',
        'test_messages',
        'test_templates',
        'test_submission',
    ]
    compile_flags = re.M | re.S

    def test_get_round_context(self):
        with fake_timezone_now(datetime(2012, 9, 8, 11, tzinfo=timezone.utc)):
            problem_instances = get_contest_problem_instances();

            instance = [inst for inst in problem_instances if inst['problem_instance'].pk == 1][0]
            self.assertEqual(instance['submission_count'], 0)
            self.assertEqual(instance['question_count'], 2)

        with fake_timezone_now(datetime(2012, 6, 4, 11, tzinfo=timezone.utc)):
            problem_instances = get_contest_problem_instances();

            instance = [inst for inst in problem_instances if inst['problem_instance'].pk == 1][0]
            self.assertEqual(instance['submission_count'], 1)
            self.assertEqual(instance['question_count'], 0)

    def test_contest_dashboard(self):
        user = User.objects.get(username='test_user')
        contest = Contest.objects.get(id='c')
        make_user_contest_admin(user, contest)

        self.assertTrue(self.client.login(username='test_user'))
        self.client.get('/c/c/')
        url = reverse('simpleui_contest_dashboard')

        response = self.client.get(url)
        content = response.content.decode('utf-8')
        self.assertEqual(response.status_code, 200)

        self.assertContains(response, 'Recent activity')
        self.assertContains(response, contest.name + '</h1>')

        submission = Submission.objects.get(id=1)
        problem_name = r'Sum.*yce \(zad1\)'
        problem_score = submission.score.to_int()

        regex = '.*<tr>.*' + problem_name + '.*OK.*' + str(problem_score) + '.*</tr>.*'
        regex = re.compile(regex, self.compile_flags)
        self.assertTrue(regex.match(content))

        # This test expects that there is no reply to the message with id=1
        message = Message.objects.get(id=1)
        regex = '.*<tr>.*General.*' + message.topic + '.*QUESTION.*</tr>.*'
        regex = re.compile(regex, self.compile_flags)
        self.assertTrue(regex.match(content))

        regex = '.*problem__solved--low.*0 / 1.*'
        regex = re.compile(regex, self.compile_flags)
        self.assertTrue(regex.match(content))

    def test_open_contest_dashboard(self):
        user = User.objects.get(username='test_user')
        contest = Contest.objects.get(id='c')
        make_user_contest_admin(user, contest)

        self.assertTrue(self.client.login(username='test_user'))
        self.client.get('/c/c/')
        url = reverse('simpleui_contest_dashboard')

        response = self.client.get(url)
        self.assertNotContains(response, 'pointsChart')

    def test_not_open_contest_dashboard(self):
        user = User.objects.get(username='test_user')
        contest = Contest.objects.get(id='c')
        make_user_contest_admin(user, contest)

        change_contest_type(contest)

        self.assertTrue(self.client.login(username='test_user'))
        self.client.get('/c/c/')
        url = reverse('simpleui_contest_dashboard')

        response = self.client.get(url)
        self.assertContains(response, 'pointsChart', count=1)

    def test_contest_dashboard_lacking_permissions(self):
        self.assertTrue(self.client.login(username='test_user'))
        self.client.get('/c/c/')
        url = reverse('simpleui_contest_dashboard')

        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

    def test_contest_dashboard_no_rounds(self):
        user = User.objects.get(username='test_user')
        contest = Contest.objects.get(id='c')
        make_user_contest_admin(user, contest)

        rounds = Round.objects.filter(contest=contest)
        for rnd in rounds:
            rnd.delete()

        self.assertTrue(self.client.login(username='test_user'))
        self.client.get('/c/c/')
        url = reverse('simpleui_contest_dashboard')

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        self.assertContains(response, '<p>There are no rounds in this contest.</p>')


class TestUserDashboard(TestCase):
    fixtures = [
        'test_users',
        'test_contest',
        'test_full_package',
        'test_problem_instance',
        'test_messages',
        'test_templates',
        'test_submission',
    ]
    compile_flags = re.M | re.S

    def test_permissions(self):
        self.assertTrue(self.client.login(username='test_user'))
        url = reverse('simpleui_user_dashboard')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        user = User.objects.get(username='test_user')
        c = Contest.objects.get(id='c')
        make_user_contest_admin(user, c)

        url = reverse('simpleui_user_dashboard')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        self.assertTrue(self.client.login(username='test_admin'))
        url = reverse('simpleui_user_dashboard')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    @override_settings(ARCHIVE_USERCONTESTS=True)
    def test_permissions_invisible(self):
        self.assertTrue(self.client.login(username='test_user'))
        url = reverse('simpleui_user_dashboard')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

    def test_user_dashboard(self):
        user = User.objects.get(username='test_user')
        c = Contest.objects.get(id='c')
        make_user_contest_admin(user, c)

        self.assertTrue(self.client.login(username='test_user'))
        url = reverse('simpleui_user_dashboard')
        response = self.client.get(url)
        content = response.content.decode('utf-8')

        self.assertEqual(response.status_code, 200)

        regex = '.*">' + c.name + '</a>.*'
        regex = re.compile(regex, self.compile_flags)
        self.assertTrue(regex.match(content))

        self.assertContains(response, '0 submissions')
        self.assertContains(response, '1 submission')
        self.assertContains(response, '0 questions')
        self.assertContains(response, '1 round')
        self.assertContains(response, '1 problem')
        self.assertNotContains(response, '0 users')
        self.assertNotContains(response, 'contest_graph')

        self.assertContains(response, 'User dashboard</h1>')

        change_contest_type(c)
        response = self.client.get(url)

        self.assertContains(response, '0 submissions')
        self.assertContains(response, '1 submission')
        self.assertContains(response, '0 questions')
        self.assertContains(response, '1 round')
        self.assertContains(response, '1 problem')
        self.assertContains(response, '0 users')
        self.assertContains(response, 'contest_graph')

        self.assertContains(response, 'User dashboard</h1>')

    def test_user_dashboard_empty(self):
        Contest.objects.all().delete()

        self.assertTrue(self.client.login(username='test_admin'))
        url = reverse('simpleui_user_dashboard')
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Create contest', count=1)
        self.assertContains(response, 'create one')
        self.assertContains(response, 'There are no contests to display.')

    def test_user_dashboard_full(self):
        user = User.objects.get(username='test_user')
        for i in range(10):
            c = Contest()
            c.name = 'tmp' + str(i)
            c.controller_name = 'oioioi.contests.controllers.ContestController'
            c.id = 'tmp' + str(i)
            c.save()

            make_user_contest_admin(user, c)

        self.assertTrue(self.client.login(username='test_user'))
        url = reverse('simpleui_user_dashboard')
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Show all contests')


class TestProblemInstance(TestCase):
    """Abstract base class with login utility for problem instance tests classes."""

    def login(self, get_problems):
        c = Contest.objects.get(id='c')
        c.controller_name = 'oioioi.teachers.controllers.TeacherContestController'
        c.save()

        user = User.objects.get(username='test_user')
        ContestPermission.objects.get_or_create(
            user=user, permission='contests.contest_admin', contest=c
        )

        self.assertTrue(self.client.login(username='test_user'))
        self.client.get('/c/c/')

        if get_problems:
            pi = ProblemInstance.objects.filter(contest=c)[0]
            p = pi.problem

            return pi, p

        return c


class TestProblemInstanceSettings(TestProblemInstance):
    fixtures = [
        'test_users',
        'teachers',
        'test_contest',
        'test_full_package',
        'test_problem_instance',
        'test_messages',
        'test_templates',
        'test_submission',
    ]

    form_data = {
        'pif-TOTAL_FORMS': '1',
        'pif-INITIAL_FORMS': '1',
        'pif-MIN_NUM_FORMS': '0',
        'pif-MAX_NUM_FORMS': '1000',
        'pif-0-id': '1',
        'pif-0-round': '1',
        'pif-0-submissions_limit': '10',
        'form-TOTAL_FORMS': '6',
        'form-INITIAL_FORMS': '6',
        'form-MIN_NUM_FORMS': '0',
        'form-MAX_NUM_FORMS': '1000',
        'form-0-name': '0',
        'form-0-time_limit': '10000',
        'form-0-memory_limit': '133000',
        'form-0-max_score': '0',
        'form-0-kind': 'EXAMPLE',
        'form-0-is_active': 'on',
        'form-0-id': '1',
        'form-1-name': '1a',
        'form-1-time_limit': '10000',
        'form-1-memory_limit': '133000',
        'form-1-max_score': '33',
        'form-1-kind': 'NORMAL',
        'form-1-is_active': 'on',
        'form-1-id': '2',
        'form-2-name': '1b',
        'form-2-time_limit': '100',
        'form-2-memory_limit': '133000',
        'form-2-max_score': '33',
        'form-2-kind': 'NORMAL',
        'form-2-is_active': 'on',
        'form-2-id': '3',
        'form-3-name': '1ocen',
        'form-3-time_limit': '10000',
        'form-3-memory_limit': '133000',
        'form-3-max_score': '0',
        'form-3-kind': 'EXAMPLE',
        'form-3-is_active': 'on',
        'form-3-id': '4',
        'form-4-name': '2',
        'form-4-time_limit': '10000',
        'form-4-memory_limit': '133000',
        'form-4-max_score': '33',
        'form-4-kind': 'NORMAL',
        'form-4-is_active': 'on',
        'form-4-id': '5',
        'form-5-name': '3',
        'form-5-time_limit': '10000',
        'form-5-memory_limit': '133000',
        'form-5-max_score': '34',
        'form-5-kind': 'NORMAL',
        'form-5-is_active': 'on',
        'form-5-id': '6',
    }

    def test_test_settings_ok(self):
        c = self.login(get_problems=False)
        pi = ProblemInstance.objects.filter(contest=c)[0]

        form_data = self.form_data.copy()
        form_data['form-0-max_score'] = '44'
        form_data['form-1-memory_limit'] = '1337'
        form_data['form-3-time_limit'] = '666'

        self.client.post(
            reverse(
                'simpleui_problem_settings', kwargs={'problem_instance_id': str(pi.id)}
            ),
            form_data,
            follow=True,
        )

        self.assertEqual(Test.objects.get(id=1).max_score, 44)
        self.assertEqual(Test.objects.get(id=2).memory_limit, 1337)
        self.assertEqual(Test.objects.get(id=4).time_limit, 666)

    @override_settings(MAX_TEST_TIME_LIMIT_PER_PROBLEM=6000)
    def test_time_limit(self):
        c = self.login(get_problems=False)
        pi = ProblemInstance.objects.filter(contest=c)[0]

        response = self.client.post(
            reverse(
                'simpleui_problem_settings', kwargs={'problem_instance_id': str(pi.id)}
            ),
            self.form_data,
            follow=True,
        )
        self.assertContains(
            response,
            "Sum of time limits for all tests is too big. It's "
            "51s, but it shouldn't exceed 6s.",
            html=True,
        )

    @override_settings(MAX_MEMORY_LIMIT_FOR_TEST=100)
    def test_memory_limit(self):
        c = self.login(get_problems=False)
        pi = ProblemInstance.objects.filter(contest=c)[0]

        response = self.client.post(
            reverse(
                'simpleui_problem_settings', kwargs={'problem_instance_id': str(pi.id)}
            ),
            self.form_data,
            follow=True,
        )
        self.assertContains(
            response,
            "Memory limit mustn't be greater than %dKiB."
            % settings.MAX_MEMORY_LIMIT_FOR_TEST,
            html=True,
        )


class TestProblemInstanceValidation(TestProblemInstance):
    fixtures = [
        'test_users',
        'teachers',
        'test_contest',
        'test_full_package',
        'test_problem_instance',
    ]

    form_data = {
        'pif-TOTAL_FORMS': '1',
        'pif-INITIAL_FORMS': '1',
        'pif-MIN_NUM_FORMS': '0',
        'pif-MAX_NUM_FORMS': '1000',
        'pif-0-id': '1',
        'pif-0-round': '1',
        'pif-0-submissions_limit': '10',
        'form-TOTAL_FORMS': '6',
        'form-INITIAL_FORMS': '6',
        'form-MIN_NUM_FORMS': '0',
        'form-MAX_NUM_FORMS': '1000',
        'form-0-name': '0',
        'form-0-time_limit': '10000',
        'form-0-memory_limit': '133000',
        'form-0-max_score': '0',
        'form-0-kind': 'EXAMPLE',
        'form-0-is_active': 'on',
        'form-0-id': '1',
        'form-1-name': '1a',
        'form-1-time_limit': '10000',
        'form-1-memory_limit': '133000',
        'form-1-max_score': '45',
        'form-1-kind': 'NORMAL',
        'form-1-is_active': 'on',
        'form-1-id': '2',
        'form-2-name': '1b',
        'form-2-time_limit': '100',
        'form-2-memory_limit': '133000',
        'form-2-max_score': '33',
        'form-2-kind': 'NORMAL',
        'form-2-is_active': 'on',
        'form-2-id': '3',
        'form-3-name': '1ocen',
        'form-3-time_limit': '10000',
        'form-3-memory_limit': '133000',
        'form-3-max_score': '0',
        'form-3-kind': 'EXAMPLE',
        'form-3-is_active': 'on',
        'form-3-id': '4',
        'form-4-name': '2',
        'form-4-time_limit': '10000',
        'form-4-memory_limit': '133000',
        'form-4-max_score': '33',
        'form-4-kind': 'NORMAL',
        'form-4-is_active': 'on',
        'form-4-id': '5',
        'form-5-name': '3',
        'form-5-time_limit': '10000',
        'form-5-memory_limit': '133000',
        'form-5-max_score': '34',
        'form-5-kind': 'NORMAL',
        'form-5-is_active': 'on',
        'form-5-id': '6',
    }

    def test_max_scores(self):
        c = self.login(get_problems=False)
        pi = ProblemInstance.objects.filter(contest=c)[0]
        response = self.client.post(
            reverse(
                'simpleui_problem_settings', kwargs={'problem_instance_id': str(pi.id)}
            ),
            self.form_data,
            follow=True,
        )
        self.assertContains(
            response, "Scores for tests in the same group must be equal"
        )
