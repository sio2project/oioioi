import pytest
import urllib.parse
from django.core.files.base import ContentFile
from django.db import transaction
from django.test import TransactionTestCase
from django.test.utils import override_settings
from django.urls import reverse

from oioioi.base.tests import needs_linux
from oioioi.contests.models import Contest, ProblemInstance, Round
from oioioi.filetracker.tests import TestStreamingMixin
from oioioi.problems.models import Problem, ProblemPackage, ProblemSite
from oioioi.problems.tests.utilities import get_test_filename


def make_add_update_problem_url(contest, args):
    return '{}?{}'.format(
        reverse('add_or_update_problem', kwargs={'contest_id': contest.id}),
        urllib.parse.urlencode(args),
    )


@override_settings(
    PROBLEM_PACKAGE_BACKENDS=('oioioi.problems.tests.DummyPackageBackend',)
)
class TestAPIProblemUpload(TransactionTestCase):
    fixtures = ['test_users', 'test_contest']

    def test_successful_upload(self):
        ProblemInstance.objects.all().delete()
        contest = Contest.objects.get()
        round = contest.round_set.all().first()
        self.assertTrue(self.client.login(username='test_admin'))
        data = {
            'package_file': ContentFile('eloziom', name='foo'),
            'contest_id': contest.id,
            'round_name': round.name,
        }
        url = reverse('api_package_upload')
        response = self.client.post(url, data, follow=True)
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertTrue('package_id' in data)

    def test_successful_reupload(self):
        # first we upload single problem
        ProblemInstance.objects.all().delete()
        contest = Contest.objects.get()
        round = contest.round_set.all().first()
        self.assertTrue(self.client.login(username='test_admin'))
        data = {
            'package_file': ContentFile('eloziom', name='foo'),
            'contest_id': contest.id,
            'round_name': round.name,
        }
        url = reverse('api_package_upload')
        response = self.client.post(url, data, follow=True)
        self.assertEqual(response.status_code, 201)
        # then we reupload its package
        problem = Problem.objects.all().first()
        data = {
            'package_file': ContentFile('eloziomReuploaded', name='foo'),
            'problem_id': problem.id,
        }
        url = reverse('api_package_reupload')
        response = self.client.post(url, data, follow=True)
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertTrue('package_id' in data)

    def test_failed_upload_no_perm(self):
        ProblemInstance.objects.all().delete()
        contest = Contest.objects.get()
        round = contest.round_set.all().first()
        self.assertTrue(self.client.login(username='test_user'))
        data = {
            'package_file': ContentFile('eloziom', name='foo'),
            'contest_id': contest.id,
            'round_name': round.name,
        }
        url = reverse('api_package_upload')
        response = self.client.post(url, data, follow=True)
        self.assertEqual(response.status_code, 403)

    def test_failed_reupload_no_perm(self):
        ProblemInstance.objects.all().delete()
        contest = Contest.objects.get()
        round = contest.round_set.all().first()
        self.assertTrue(self.client.login(username='test_admin'))
        data = {
            'package_file': ContentFile('eloziom', name='foo'),
            'contest_id': contest.id,
            'round_name': round.name,
        }
        url = reverse('api_package_upload')
        response = self.client.post(url, data, follow=True)
        self.assertEqual(response.status_code, 201)

        self.assertTrue(self.client.login(username='test_user'))
        problem = Problem.objects.all().first()
        data = {
            'package_file': ContentFile('eloziomReuploaded', name='foo'),
            'problem_id': problem.id,
        }
        url = reverse('api_package_reupload')
        response = self.client.post(url, data, follow=True)
        self.assertEqual(response.status_code, 403)

    def test_failed_upload_no_file(self):
        ProblemInstance.objects.all().delete()
        contest = Contest.objects.get()
        round = contest.round_set.all().first()
        self.assertTrue(self.client.login(username='test_admin'))
        data = {'contest_id': contest.id, 'round_name': round.name}
        url = reverse('api_package_upload')
        response = self.client.post(url, data, follow=True)
        self.assertEqual(response.status_code, 400)

    def test_failed_upload_no_contest_id(self):
        ProblemInstance.objects.all().delete()
        contest = Contest.objects.get()
        round = contest.round_set.all().first()
        self.assertTrue(self.client.login(username='test_admin'))
        data = {
            'package_file': ContentFile('eloziom', name='foo'),
            'round_name': round.name,
        }
        url = reverse('api_package_upload')
        response = self.client.post(url, data, follow=True)
        self.assertEqual(response.status_code, 400)

    def test_failed_upload_no_round_name(self):
        ProblemInstance.objects.all().delete()
        contest = Contest.objects.get()
        self.assertTrue(self.client.login(username='test_admin'))
        data = {
            'package_file': ContentFile('eloziom', name='foo'),
            'contest_id': contest.id,
        }
        url = reverse('api_package_upload')
        response = self.client.post(url, data, follow=True)
        self.assertEqual(response.status_code, 400)

    def test_failed_reupload_no_file(self):
        ProblemInstance.objects.all().delete()
        self.assertTrue(self.client.login(username='test_admin'))
        data = {'problem_id': 1}
        url = reverse('api_package_reupload')
        response = self.client.post(url, data, follow=True)
        self.assertEqual(response.status_code, 400)

    def test_failed_reupload_no_problem_id(self):
        ProblemInstance.objects.all().delete()
        self.assertTrue(self.client.login(username='test_admin'))
        data = {'package_file': ContentFile('eloziom', name='foo')}
        url = reverse('api_package_reupload')
        response = self.client.post(url, data, follow=True)
        self.assertEqual(response.status_code, 400)


@override_settings(
    PROBLEM_PACKAGE_BACKENDS=('oioioi.problems.tests.DummyPackageBackend',)
)
class TestAPIProblemUploadQuery(TransactionTestCase):
    fixtures = ['test_users', 'test_contest', 'test_permissions']

    def setUp(self):
        ProblemInstance.objects.all().delete()
        self.contest = Contest.objects.get()
        self.round = self.contest.round_set.all().first()
        self.data = {
            'package_file': ContentFile('eloziom', name='foo'),
            'contest_id': self.contest.id,
            'round_name': self.round.name,
        }

    def _test_successful_query(self, username):
        self.assertTrue(self.client.login(username=username))
        url = reverse('api_package_upload')
        response = self.client.post(url, self.data, follow=True)
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertTrue('package_id' in data)
        package_id = data.get('package_id')
        url = reverse('api_package_upload_query', args=(package_id,))
        response = self.client.get(url, follow=True)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue('package_status' in data)

    def test_successful_query_as_admin(self):
        self._test_successful_query('test_admin')

    def test_successful_query_as_contest_admin(self):
        self._test_successful_query('test_contest_admin')

    def test_failed_query_no_perm(self):
        self.assertTrue(self.client.login(username='test_admin'))
        url = reverse('api_package_upload')
        response = self.client.post(url, self.data, follow=True)
        self.assertEqual(response.status_code, 201)
        self.assertTrue(self.client.login(username='test_user'))
        package_id = response.json().get('package_id')
        url = reverse('api_package_upload_query', args=(package_id,))
        response = self.client.get(url, follow=True)
        self.assertEqual(response.status_code, 403)


@override_settings(
    PROBLEM_PACKAGE_BACKENDS=('oioioi.problems.tests.DummyPackageBackend',)
)
class TestProblemUpload(TransactionTestCase):
    fixtures = ['test_users', 'test_contest']

    def test_successful_upload(self):
        ProblemInstance.objects.all().delete()
        contest = Contest.objects.get()
        self.assertTrue(self.client.login(username='test_admin'))
        data = {
            'package_file': ContentFile('eloziom', name='foo'),
            'visibility': Problem.VISIBILITY_FRIENDS,
        }
        url = make_add_update_problem_url(contest, {'key': 'upload'})
        response = self.client.post(url, data, follow=True)
        self.assertContains(response, 'Package information')
        self.assertContains(response, 'Edit problem')
        self.assertNotContains(response, 'Error details')
        self.assertNotContains(response, 'Model solutions')
        package = ProblemPackage.objects.get()
        self.assertEqual(package.status, 'OK')
        self.assertEqual(package.problem_name, 'bar')
        problem = Problem.objects.get()
        self.assertEqual(problem.short_name, 'bar')
        problem_instance = ProblemInstance.objects.filter(contest__isnull=False).get()
        self.assertEqual(problem_instance.contest, contest)
        self.assertEqual(problem_instance.problem, problem)

    def test_failed_upload(self):
        ProblemInstance.objects.all().delete()
        contest = Contest.objects.get()
        self.assertTrue(self.client.login(username='test_admin'))
        data = {
            'package_file': ContentFile('eloziom', name='FAIL'),
            'visibility': Problem.VISIBILITY_FRIENDS,
        }
        url = make_add_update_problem_url(contest, {'key': 'upload'})
        response = self.client.post(url, data, follow=True)
        self.assertContains(response, 'DUMMY_FAILURE')
        self.assertContains(response, 'Error details')
        self.assertNotContains(response, 'Edit problem')
        self.assertNotContains(response, 'Model solutions')
        package = ProblemPackage.objects.get()
        self.assertEqual(package.problem_name, 'bar')
        self.assertEqual(package.status, 'ERR')
        problems = Problem.objects.all()
        self.assertEqual(len(problems), 0)
        problem_instances = ProblemInstance.objects.all()
        self.assertEqual(len(problem_instances), 0)

    @override_settings(PROBLEM_SOURCES=('oioioi.problems.tests.DummySource',))
    def test_handlers(self):
        contest = Contest.objects.get()
        self.assertTrue(self.client.login(username='test_admin'))
        data = {
            'package_file': ContentFile('eloziom', name='foo'),
            'visibility': Problem.VISIBILITY_FRIENDS,
        }
        url = make_add_update_problem_url(contest, {'key': 'upload'})
        response = self.client.post(url, data, follow=True)
        self.assertContains(response, 'Package information')
        package = ProblemPackage.objects.get()
        self.assertEqual(package.status, 'OK')
        self.assertEqual(package.problem_name, 'handled')

    def test_contest_controller_plugins(self):
        contest = Contest.objects.get()
        contest.controller_name = 'oioioi.problems.tests.DummyContestController'
        contest.save()

        self.assertTrue(self.client.login(username='test_admin'))
        data = {
            'package_file': ContentFile('eloziom', name='foo'),
            'visibility': Problem.VISIBILITY_FRIENDS,
            'cc_rulez': True,
        }
        url = make_add_update_problem_url(contest, {'key': 'upload'})
        response = self.client.post(url, data, follow=True)
        self.assertContains(response, 'Package information')
        package = ProblemPackage.objects.get()
        self.assertEqual(package.status, 'OK')
        self.assertEqual(package.problem_name, 'contest_controller_rulez')

    def test_problem_submission_limit_changed(self):
        contest = Contest.objects.get()
        package_file = ContentFile('eloziom', name='foo')
        self.assertTrue(self.client.login(username='test_admin'))
        url = reverse('oioioiadmin:problems_problem_add')
        response = self.client.get(url, {'contest_id': contest.id}, follow=True)
        url = response.redirect_chain[-1][0]
        self.assertEqual(response.status_code, 200)

        response = self.client.post(
            url,
            {'package_file': package_file, 'visibility': Problem.VISIBILITY_FRIENDS},
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Problem.objects.count(), 1)
        self.assertEqual(ProblemInstance.objects.count(), 2)

        problem = ProblemInstance.objects.filter(contest__isnull=False).get().problem
        contest.default_submissions_limit += 100
        contest.save()

        url = make_add_update_problem_url(contest, {'problem': problem.id})
        response = self.client.get(url, follow=True)
        url = response.redirect_chain[-1][0]
        self.assertEqual(response.status_code, 200)
        response = self.client.post(
            url,
            {'package_file': package_file, 'visibility': Problem.VISIBILITY_FRIENDS},
            follow=True,
        )
        self.assertEqual(response.status_code, 200)

        pis = ProblemInstance.objects.filter(problem=problem)
        self.assertEqual(pis.count(), 2)

        pi = ProblemInstance.objects.get(contest__isnull=False)
        self.assertEqual(pi.submissions_limit, contest.default_submissions_limit - 100)


@needs_linux
class TestProblemsetUploading(TransactionTestCase, TestStreamingMixin):
    fixtures = ['test_users', 'test_contest']

    def post_package_file(self, url, filename, visibility=Problem.VISIBILITY_PRIVATE):
        return self.client.post(
            url,
            {
                'package_file': open(filename, 'rb'),
                'visibility': visibility,
            },
            follow=True,
        )

    def check_models_for_simple_package(self, problem_instance):
        url = reverse('model_solutions', args=[problem_instance.id])
        response = self.client.post(url, follow=True)
        self.assertEqual(response.status_code, 200)
        to_find = ["0", "1a", "1b", "1c", "2"]
        for test in to_find:
            self.assertContains(response, ">" + test + "</th>")

    @pytest.mark.xfail(strict=True)
    def test_upload_problem(self):
        filename = get_test_filename('test_simple_package.zip')
        self.assertTrue(self.client.login(username='test_admin'))

        # add problem to problemset
        url = reverse('problemset_add_or_update')
        # not possible from problemset :)
        response = self.client.get(url, {'key': "problemset_source"}, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Option not available")
        self.assertContains(response, "Add problem")
        self.assertNotContains(response, "Select")
        # but ok by package
        response = self.client.get(url, follow=True)
        url = response.redirect_chain[-1][0]
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Add problem")
        self.assertIn(
            'problems/problemset/add-or-update.html',
            [getattr(t, 'name', None) for t in response.templates],
        )

        response = self.post_package_file(url, filename)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Problem.objects.count(), 1)
        self.assertEqual(ProblemInstance.objects.count(), 1)
        self.assertEqual(ProblemSite.objects.count(), 1)

        # problem is not visible in "Public"
        url = reverse('problemset_main')
        response = self.client.post(url, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Testowe")
        self.assertNotContains(response, "<td>tst</td>")
        # but visible in "My problems"
        url = reverse('problemset_my_problems')
        self.assertEqual(response.status_code, 200)
        response = self.client.post(url, follow=True)
        self.assertContains(response, "Testowe")
        self.assertContains(response, "<td>tst</td>")
        # and we are problem's author and problem_site exists
        problem = Problem.objects.get()
        url = '{}?key=settings'.format(
            reverse('problem_site', args=[problem.problemsite.url_key])
        )
        response = self.client.post(url, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Edit problem')
        self.assertContains(response, 'Reupload problem')
        self.assertContains(response, 'Edit package')
        self.assertContains(response, 'Model solutions')
        # we can see model solutions of main_problem_instance
        self.check_models_for_simple_package(problem.main_problem_instance)

        # reuploading problem in problemset is not available from problemset
        url = reverse('problemset_add_or_update')
        response = self.client.get(
            url, {'key': "problemset_source", 'problem': problem.id}, follow=True
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Option not available")
        self.assertNotContains(response, "Select")

    @pytest.mark.xfail(strict=True)
    def test_add_problem_to_contest(self):
        ProblemInstance.objects.all().delete()

        contest = Contest.objects.get()
        contest.default_submissions_limit = 42
        contest.save()
        filename = get_test_filename('test_simple_package.zip')
        self.assertTrue(self.client.login(username='test_admin'))
        # Add problem to problemset
        url = reverse('problemset_add_or_update')
        response = self.client.get(url, follow=True)
        url = response.redirect_chain[-1][0]
        self.assertEqual(response.status_code, 200)

        response = self.post_package_file(url, filename)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Problem.objects.count(), 1)
        self.assertEqual(ProblemInstance.objects.count(), 1)

        problem = Problem.objects.get()
        url_key = problem.problemsite.url_key

        # now, add problem to the contest
        url = make_add_update_problem_url(contest, {'key': "problemset_source"})
        response = self.client.post(url, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Add from Problemset')
        self.assertContains(response, 'Enter problem')
        self.assertContains(response, 's secret key')
        self.assertContains(response, 'Choose problem from problemset')

        pi_number = 3
        for i in range(pi_number):
            url = make_add_update_problem_url(contest, {'key': "problemset_source"})
            response = self.client.get(url, {'url_key': url_key}, follow=True)
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, str(url_key))
            response = self.client.post(url, {'url_key': url_key}, follow=True)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(ProblemInstance.objects.count(), 2 + i)

        # check submissions limit
        for pi in ProblemInstance.objects.filter(contest__isnull=False):
            self.assertEqual(pi.submissions_limit, contest.default_submissions_limit)

        # add probleminstances to round
        with transaction.atomic():
            for pi in ProblemInstance.objects.filter(contest__isnull=False):
                pi.round = Round.objects.get()
                pi.save()

        # we can see model solutions
        pi = ProblemInstance.objects.filter(contest__isnull=False)[0]
        self.check_models_for_simple_package(pi)

        # tests and models of every problem_instance are independent
        num_tests = pi.test_set.count()
        for test in pi.test_set.all():
            test.delete()
        pi.save()

        url = reverse('model_solutions', args=[pi.id])
        response = self.client.post(url, follow=True)
        self.assertEqual(response.status_code, 200)
        for test in ["0", "1a", "1b", "1c", "2"]:
            self.assertNotContains(response, ">" + test + "</th>")

        for pi2 in ProblemInstance.objects.all():
            if pi2 != pi:
                self.assertEqual(pi2.test_set.count(), num_tests)
                self.check_models_for_simple_package(pi2)

        # reupload one ProblemInstance from problemset
        url = make_add_update_problem_url(
            contest,
            {
                'key': "problemset_source",
                'problem': problem.id,
                'instance_id': pi.id,
            },
        )
        response = self.client.get(url, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, str(url_key))
        self.assertNotContains(response, "Select")
        response = self.client.post(url, {'url_key': url_key}, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(ProblemInstance.objects.count(), pi_number + 1)
        self.assertTrue(pi.round)
        self.assertEqual(pi.test_set.count(), num_tests)
        self.check_models_for_simple_package(pi)
        self.assertContains(response, "1 PROBLEM NEEDS REJUDGING")
        self.assertEqual(
            response.content.count("Rejudge all submissions for problem"), 1
        )

        # reupload problem in problemset
        url = '{}?{}'.format(
            reverse('problemset_add_or_update'),
            urllib.parse.urlencode({'problem': problem.id}),
        )
        response = self.client.get(url, follow=True)
        url = response.redirect_chain[-1][0]
        self.assertEqual(response.status_code, 200)
        response = self.post_package_file(url, filename)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(ProblemInstance.objects.count(), pi_number + 1)
        self.assertContains(response, "3 PROBLEMS NEED REJUDGING")
        self.check_models_for_simple_package(pi)

        # rejudge one problem
        url = reverse('rejudge_all_submissions_for_problem', args=[pi.id])
        response = self.client.get(url, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "You are going to rejudge 1")
        response = self.client.post(url, {'submit': True}, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.content.count("Rejudge all submissions for problem"), pi_number - 1
        )
        self.assertContains(response, "1 rejudge request received.")

    def test_uploading_to_contest(self):
        # we can add problem directly from contest
        contest = Contest.objects.get()
        filename = get_test_filename('test_simple_package.zip')
        self.assertTrue(self.client.login(username='test_admin'))
        url = reverse('oioioiadmin:problems_problem_add')
        response = self.client.get(url, {'contest_id': contest.id}, follow=True)
        url = response.redirect_chain[-1][0]
        self.assertEqual(response.status_code, 200)
        self.assertIn(
            'problems/add-or-update.html',
            [getattr(t, 'name', None) for t in response.templates],
        )
        response = self.post_package_file(url, filename)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Problem.objects.count(), 1)
        self.assertEqual(ProblemInstance.objects.count(), 2)

        # many times
        response = self.post_package_file(url, filename)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Problem.objects.count(), 2)
        self.assertEqual(ProblemInstance.objects.count(), 4)

        # and nothing needs rejudging
        self.assertNotContains(response, 'REJUDGING')
