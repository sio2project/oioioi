from django.test import TestCase
from django.core.urlresolvers import reverse
from oioioi.base.tests import check_not_accessible
from oioioi.contests.models import Contest
from oioioi.problems.controllers import ProblemController
from oioioi.problems.models import Problem, ProblemStatement, \
        make_problem_filename

class TestProblemController(ProblemController):
    pass

class TestModels(TestCase):
    def test_problem_controller_property(self):
        problem = Problem(controller_name=
                'oioioi.problems.tests.TestProblemController')
        self.assert_(isinstance(problem.controller, TestProblemController))

    def test_make_problem_filename(self):
        p12 = Problem(pk=12)
        self.assertEqual(make_problem_filename(p12, 'a/hej.txt'),
                'problems/12/hej.txt')
        ps = ProblemStatement(pk=22, problem=p12)
        self.assertEqual(make_problem_filename(ps, 'a/hej.txt'),
                'problems/12/hej.txt')

class TestProblemViews(TestCase):
    fixtures = ['test_users', 'test_contest', 'test_full_package']

    def test_problem_statement_view(self):
        self.client.login(username='test_admin')
        statement = ProblemStatement.objects.get()
        url = reverse('show_statement', kwargs={'statement_id': statement.id})
        response = self.client.get(url)
        self.assertTrue(response.content.startswith('%PDF'))

        self.client.login(username='test_user')
        response = self.client.get(url)
        self.assertIn(response.status_code, (403, 404))

    def test_admin_changelist_view(self):
        self.client.login(username='test_admin')
        url = reverse('oioioiadmin:problems_problem_changelist')
        response = self.client.get(url)
        self.assertIn('Sum', response.content)

        self.client.login(username='test_user')
        response = self.client.get(url)
        self.assertNotIn('Sum', response.content)

    def test_admin_change_view(self):
        self.client.login(username='test_admin')
        problem = Problem.objects.get()
        url = reverse('oioioiadmin:problems_problem_change',
                args=(problem.id,))
        response = self.client.get(url)
        elements_to_find = ['Sum', 'sum', '0', '1a', '1b', '1ocen', '2',
                'Example', 'Normal']
        for element in elements_to_find:
            self.assertIn(element, response.content)

    def test_admin_delete_view(self):
        self.client.login(username='test_admin')
        problem = Problem.objects.get()
        url = reverse('oioioiadmin:problems_problem_delete',
                args=(problem.id,))
        response = self.client.post(url, {'post': 'yes'})
        self.assertEqual(Problem.objects.count(), 0)

    def _test_problem_permissions(self):
        problem = Problem.objects.get()
        contest = Contest.objects.get()
        statement = ProblemStatement.objects.get()
        check_not_accessible(self, 'oioioiadmin:problems_problem_add',
                data={'package_file': open(__file__, 'rb'),
                      'contest_id': contest.id})
        check_not_accessible(self, 'oioioiadmin:problems_problem_reupload',
                args=(problem.id,))
        check_not_accessible(self, 'oioioiadmin:problems_problem_download',
                args=(problem.id,))
        check_not_accessible(self, 'oioioiadmin:problems_problem_change',
                args=(problem.id,))
        check_not_accessible(self, 'oioioiadmin:problems_problem_delete',
                args=(problem.id,))
        check_not_accessible(self, 'show_statement',
                kwargs={'statement_id': statement.id})

    def test_problem_permissions(self):
        self._test_problem_permissions()
        self.client.login(username='test_user')
        self._test_problem_permissions()
