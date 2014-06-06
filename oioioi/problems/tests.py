import os.path
import urllib

from django.contrib.auth.models import User, Permission
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase
from django.core.urlresolvers import reverse
from nose.tools import nottest

from oioioi.base.tests import check_not_accessible
from oioioi.contests.models import Contest, ProblemInstance
from oioioi.filetracker.tests import TestStreamingMixin
from oioioi.problems.controllers import ProblemController
from oioioi.problems.models import Problem, ProblemStatement, \
        make_problem_filename


class TestProblemController(ProblemController):
    def fill_evaluation_environ(self, environ, **kwargs):
        raise NotImplementedError


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


@nottest
def get_test_filename(name):
    import oioioi.sinolpack
    return os.path.join(os.path.dirname(oioioi.sinolpack.__file__), 'files',
                        name)


class TestProblemViews(TestCase, TestStreamingMixin):
    fixtures = ['test_users', 'test_contest', 'test_full_package']

    def test_problem_statement_view(self):
        self.client.login(username='test_admin')
        statement = ProblemStatement.objects.get()
        url = reverse('show_statement', kwargs={'statement_id': statement.id})
        response = self.client.get(url)
        content = self.streamingContent(response)
        self.assertTrue(content.startswith('%PDF'))

        self.client.login(username='test_user')
        response = self.client.get(url)
        self.assertIn(response.status_code, (403, 404))

    def test_admin_changelist_view(self):
        self.client.login(username='test_admin')
        url = reverse('oioioiadmin:problems_problem_changelist')
        response = self.client.get(url)
        self.assertContains(response, 'Sum')

        self.client.login(username='test_user')
        check_not_accessible(self, url)

        user = User.objects.get(username='test_user')
        content_type = ContentType.objects.get_for_model(Problem)
        permission = Permission.objects.get(content_type=content_type,
                                            codename='problems_db_admin')
        user.user_permissions.add(permission)
        response = self.client.get(url)
        self.assertContains(response, 'Sum')

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
        self.client.post(url, {'post': 'yes'})
        self.assertEqual(Problem.objects.count(), 0)

    def _test_problem_permissions(self):
        problem = Problem.objects.get()
        contest = Contest.objects.get()
        statement = ProblemStatement.objects.get()
        check_not_accessible(self, 'oioioiadmin:problems_problem_add',
                data={'package_file': open(__file__, 'rb'),
                      'contest_id': contest.id})
        check_not_accessible(self, 'add_or_update_contest_problem',
                kwargs={'contest_id': contest.id}, qs={'problem': problem.id})
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

    def test_problem_submission_limit_changed(self):
        ProblemInstance.objects.all().delete()
        Problem.objects.all().delete()

        contest = Contest.objects.get()
        filename = get_test_filename('test_simple_package.zip')
        self.client.login(username='test_admin')
        url = reverse('oioioiadmin:problems_problem_add')
        response = self.client.get(url, {'contest_id': contest.id},
                follow=True)
        url = response.redirect_chain[-1][0]
        self.assertEqual(response.status_code, 200)

        response = self.client.post(url,
                {'package_file': open(filename, 'rb')}, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Problem.objects.count(), 1)
        self.assertEqual(ProblemInstance.objects.count(), 1)

        problem = ProblemInstance.objects.get().problem
        contest.default_submissions_limit += 100
        contest.save()

        url = reverse('add_or_update_contest_problem',
                kwargs={'contest_id': contest.id}) + '?' + \
                        urllib.urlencode({'problem': problem.id})
        response = self.client.get(url, follow=True)
        url = response.redirect_chain[-1][0]
        self.assertEqual(response.status_code, 200)
        response = self.client.post(url,
                {'package_file': open(filename, 'rb')}, follow=True)
        self.assertEqual(response.status_code, 200)

        pis = ProblemInstance.objects.filter(problem=problem)
        self.assertEqual(pis.count(), 1)
