from oioioi.base.tests import TestCase
from django.urls import reverse
from oioioi.contests.models import ProblemInstance
from oioioi.problems.models import Problem


class TestInteractiveProblemController(TestCase):
    fixtures = ['test_users', 'test_contest', 'test_interactive']

    def test_test_runs(self):
        self.assertTrue(self.client.login(username='test_admin'))
        self.client.get('/c/c/')
        problem_instance = ProblemInstance.objects.all()[1]
        url = reverse(
            'oioioiadmin:contests_probleminstance_change', args=(problem_instance.id,)
        )

        response = self.client.get(url)
        self.assertNotContains(response, "Test run config")

    def test_advanced_settings(self):
        self.assertTrue(self.client.login(username='test_admin'))
        self.client.get('/c/c/')
        problem = Problem.objects.all()[0]
        url = reverse(
            'oioioiadmin:problems_problem_change', args=(problem.id,)
        )

        response = self.client.get(url)
        self.assertContains(response, "Interactive programming problem")
