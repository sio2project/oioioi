# coding: utf-8

import io

import six
import urllib.parse
from django.conf import settings
from django.contrib.auth.models import AnonymousUser, Permission, User
from django.contrib.contenttypes.models import ContentType
from django.core.files.base import ContentFile
from django.test import RequestFactory
from django.test.utils import override_settings
from django.urls import reverse

from oioioi.base.tests import TestCase, check_not_accessible
from oioioi.contests.current_contest import ContestMode
from oioioi.contests.models import Contest, ProblemInstance
from oioioi.filetracker.tests import TestStreamingMixin
from oioioi.problems.models import (
    AlgorithmTag,
    AlgorithmTagThrough,
    DifficultyTag,
    DifficultyTagThrough,
    Problem,
    ProblemName,
    ProblemAttachment,
    ProblemPackage,
    ProblemStatement,
)
from oioioi.problems.problem_site import problem_site_tab
from oioioi.problems.tests.utilities import AssertContainsOnlyMixin, get_test_filename


class TestProblemViews(TestCase, TestStreamingMixin):
    fixtures = [
        'test_users',
        'test_contest',
        'test_full_package',
        'test_problem_instance',
        'test_permissions',
    ]

    def post_package_file(self, url, filename, visibility=Problem.VISIBILITY_PRIVATE):
        return self.client.post(
            url,
            {
                'package_file': open(filename, 'rb'),
                'visibility': visibility,
            },
            follow=True,
        )

    def test_problem_statement_view(self):
        # superuser
        self.assertTrue(self.client.login(username='test_admin'))
        statement = ProblemStatement.objects.get()

        self.client.get('/c/c/')  # 'c' becomes the current contest
        url = reverse('show_statement', kwargs={'statement_id': statement.id})

        response = self.client.get(url)
        content = self.streamingContent(response)
        self.assertTrue(content.startswith(b'%PDF'))
        # contest admin
        self.assertTrue(self.client.login(username='test_contest_admin'))
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        content = self.streamingContent(response)
        self.assertTrue(content.startswith(b'%PDF'))

        self.assertTrue(self.client.login(username='test_user'))
        response = self.client.get(url)
        self.assertIn(response.status_code, (403, 404))

    def test_admin_changelist_view(self):
        self.assertTrue(self.client.login(username='test_admin'))

        self.client.get('/c/c/')  # 'c' becomes the current contest
        url = reverse('oioioiadmin:problems_problem_changelist')

        response = self.client.get(url)
        self.assertContains(response, 'Sum')

        self.assertTrue(self.client.login(username='test_user'))

        # Users with problem.problems_db_admin can only see problems with visibility set to public.
        problem = Problem.objects.get()
        problem.visibility = Problem.VISIBILITY_PUBLIC
        problem.save()

        check_not_accessible(self, url)

        user = User.objects.get(username='test_user')
        content_type = ContentType.objects.get_for_model(Problem)
        permission = Permission.objects.get(
            content_type=content_type, codename='problems_db_admin'
        )
        user.user_permissions.add(permission)
        response = self.client.get(url)
        self.assertContains(response, 'Sum')

    def test_admin_change_view(self):
        self.assertTrue(self.client.login(username='test_admin'))
        problem = Problem.objects.get()

        self.client.get('/c/c/')  # 'c' becomes the current contest
        url = reverse('oioioiadmin:problems_problem_change', args=(problem.id,))

        response = self.client.get(url)
        elements_to_find = ['Sum', 'sum']
        for element in elements_to_find:
            self.assertContains(response, element)

    def test_admin_delete_view_basic(self):
        self.assertTrue(self.client.login(username='test_admin'))
        problem = Problem.objects.get()
        self.client.get('/c/c/')  # 'c' becomes the current contest
        url = reverse('oioioiadmin:problems_problem_delete', args=(problem.id,))


        response = self.client.post(url, {'post': 'yes'}, follow=True)
        self.assertEqual(Problem.objects.count(), 0)
        self.assertEqual(response.status_code, 200)

    def test_admin_add_in_contest_delete_in_problemset(self):
        self.assertTrue(self.client.login(username='test_admin'))
        ProblemInstance.objects.all().delete()
        contest = Contest.objects.get()
        filename = get_test_filename('test_full_package.tgz')
        self.client.get('/c/c/')  # 'c' becomes the current contest
        url = reverse('admin:problems_problem_add')
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
        problem = Problem.objects.get()

        url = reverse('oioioiadmin:problems_problem_delete', args=(problem.id,),)
        response = self.client.post(url, {'post': 'yes'}, follow=True,)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Problem.objects.count(), 0)

    def test_admin_add_to_contest_delete_in_problemset(self):
        self.assertTrue(self.client.login(username='test_admin'))
        url = reverse('problemset_add_to_contest', kwargs={'site_key': '123'})
        url += '?problem_name=sum'
        response = self.client.get(url, follow=True)
        self.assertEqual(response.status_code, 200)
        problem = Problem.objects.get()
        self.assertEqual(Problem.objects.count(), 1)
        url = reverse('oioioiadmin:problems_problem_delete', args=(problem.id,),)
        response = self.client.post(url, {'post': 'yes'}, follow=True,)
        self.assertEqual(Problem.objects.count(), 0)
        self.assertEqual(response.status_code, 200)

    def _test_problem_permissions(self):
        problem = Problem.objects.get()
        contest = Contest.objects.get()
        statement = ProblemStatement.objects.get()

        with io.open(__file__, 'rb') as f:
            file = six.ensure_text(f.read())

        check_not_accessible(
            self,
            'oioioiadmin:problems_problem_add',
            data={'package_file': file, 'contest_id': contest.id},
        )
        check_not_accessible(
            self,
            'add_or_update_problem',
            kwargs={'contest_id': contest.id},
            qs={'problem': problem.id},
        )
        check_not_accessible(
            self, 'oioioiadmin:problems_problem_download', args=(problem.id,)
        )
        check_not_accessible(
            self, 'oioioiadmin:problems_problem_change', args=(problem.id,)
        )
        check_not_accessible(
            self, 'oioioiadmin:problems_problem_delete', args=(problem.id,)
        )
        check_not_accessible(
            self, 'show_statement', kwargs={'statement_id': statement.id}
        )

    def test_problem_permissions(self):
        self._test_problem_permissions()
        self.assertTrue(self.client.login(username='test_user'))
        self._test_problem_permissions()


class TestProblemPackageAdminView(TestCase):
    fixtures = [
        'test_users',
        'test_contest',
        'test_permissions',
        'test_problem_packages',
        'test_problem_instance',
        'test_two_empty_contests',
    ]

    def test_links(self):
        self.assertTrue(self.client.login(username='test_admin'))

        self.client.get('/c/c/')  # 'c' becomes the current contest
        url = reverse('oioioiadmin:problems_problempackage_changelist')

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Error details')
        self.assertContains(response, 'Edit problem')
        self.assertContains(response, 'Model solutions')

        self.client.get('/c/c1/')  # 'c1' becomes the current contest
        url = reverse('oioioiadmin:problems_problempackage_changelist')

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Error details')
        # Not visible, because the problem's contest is 'c', not 'c1'
        self.assertNotContains(response, 'Edit problem')
        # Not visible, because the problem instances's contest is 'c', not 'c1'
        self.assertNotContains(response, 'Model solutions')

    @override_settings(CONTEST_MODE=ContestMode.neutral)
    def test_navbar_links(self):
        for _ in range(0, 2):
            url = reverse('my_submissions', kwargs={'contest_id': 'c'})
            for login in ['test_admin', 'test_contest_admin']:
                self.assertTrue(self.client.login(username=login))
                self.assertContains(self.client.get(url), 'Problem packages', 2)
            # Outside of contests there is only the System Administration menu.
            url = reverse('noncontest:select_contest')
            self.assertNotContains(self.client.get(url), 'Problem packages')
            self.assertTrue(self.client.login(username='test_admin'))
            self.assertContains(self.client.get(url), 'Problem packages', 2)
            # It shouldn't matter whether there are packages with errors.
            ProblemPackage.objects.all().delete()

    def test_problem_info_brace(self):
        self.assertTrue(self.client.login(username='test_admin'))

        self.client.get('/c/c/')  # 'c' becomes the current contest
        url = reverse('oioioiadmin:problems_problempackage_changelist')

        bad_package = ProblemPackage(status="ERR", info="foo } bar")
        bad_package.save()

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)


class TestProblemPackageViews(TestCase, TestStreamingMixin):
    fixtures = [
        'test_users',
        'test_contest',
        'test_problem_packages',
        'test_problem_instance',
    ]

    def _test_package_permissions(self, is_admin=False):
        models = ['problempackage', 'contestproblempackage']
        view_prefix = 'oioioiadmin:problems_'
        package = ProblemPackage.objects.get(pk=2)
        for m in models:
            prefix = view_prefix + m + '_'
            check_not_accessible(self, prefix + 'add')
            check_not_accessible(self, prefix + 'change', args=(package.id,))
            if not is_admin:
                check_not_accessible(self, prefix + 'delete', args=(package.id,))
        if not is_admin:
            check_not_accessible(self, 'download_package', args=(package.id,))
            check_not_accessible(
                self,
                'download_package_traceback',
                kwargs={'package_id': str(package.id)},
            )

    def test_admin_changelist_view(self):
        self.assertTrue(self.client.login(username='test_admin'))

        self.client.get('/c/c/')  # 'c' becomes the current contest
        url = reverse('oioioiadmin:problems_problempackage_changelist')

        response = self.client.get(url)
        self.assertContains(response, 'XYZ')

    def test_package_file_view(self):
        package = ProblemPackage.objects.get(pk=1)
        package.package_file = ContentFile(b'eloziom', name='foo')
        package.save()
        self.assertTrue(self.client.login(username='test_admin'))

        self.client.get('/c/c/')  # 'c' becomes the current contest
        url = reverse('download_package', kwargs={'package_id': str(package.id)})

        response = self.client.get(url)
        content = self.streamingContent(response)
        self.assertEqual(content, b'eloziom')

    def test_package_traceback_view(self):
        package = ProblemPackage.objects.get(pk=2)
        package.traceback = ContentFile(b'eloziom', name='foo')
        package.save()
        self.assertTrue(self.client.login(username='test_admin'))
        self.client.get('/c/c/')  # 'c' becomes the current contest
        download_package_traceback_url = reverse(
            'download_package_traceback', kwargs={'package_id': str(package.id)}
        )

        response = self.client.get(download_package_traceback_url)
        content = self.streamingContent(response)
        self.assertEqual(content, b'eloziom')

        package.traceback = None
        package.save()
        self.assertTrue(self.client.login(username='test_admin'))
        response = self.client.get(download_package_traceback_url)
        self.assertEqual(response.status_code, 404)

    def test_package_permissions(self):
        self._test_package_permissions()
        self.assertTrue(self.client.login(username='test_user'))
        self._test_package_permissions()
        self.assertTrue(self.client.login(username='test_admin'))
        self._test_package_permissions(is_admin=True)


@override_settings(CONTEST_MODE=ContestMode.neutral)
class TestProblemSite(TestCase, TestStreamingMixin):
    fixtures = [
        'test_users',
        'test_contest',
        'test_full_package',
        'test_problem_instance_with_no_contest',
        'test_submission',
        'test_problem_site',
        'test_algorithm_tags',
        'test_difficulty_tags',
        'test_proposals',
    ]

    def setUp(self):
        problem = Problem.objects.get(id=1)
        AlgorithmTagThrough.objects.create(
            problem=problem,
            tag=AlgorithmTag.objects.get(name='dp'),
        )
        AlgorithmTagThrough.objects.create(
            problem=problem,
            tag=AlgorithmTag.objects.get(name='lcis'),
        )
        DifficultyTagThrough.objects.create(
            problem=problem,
            tag=DifficultyTag.objects.get(name='hard'),
        )

    def _get_site_urls(self):
        url = reverse('problem_site', kwargs={'site_key': '123'})
        url_statement = url + "?key=statement"
        url_submissions = url + "?key=submissions"
        return {'site': url, 'statement': url_statement, 'submissions': url_submissions}

    def _create_PA(self):
        problem = Problem.objects.get()
        pa = ProblemAttachment(
            problem=problem,
            description='problem-attachment',
            content=ContentFile(b'content-of-probatt', name='probatt.txt'),
        )
        pa.save()

    def test_default_tabs(self):
        urls = self._get_site_urls()
        response = self.client.get(urls['site'])
        self.assertRedirects(response, urls['statement'])
        response = self.client.get(urls['statement'])
        for url in urls.values():
            self.assertContains(response, url)

    def test_statement_tab(self):
        url_external_stmt = reverse(
            'problem_site_external_statement', kwargs={'site_key': '123'}
        )
        response = self.client.get(self._get_site_urls()['statement'])
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, url_external_stmt)

    def test_submissions_tab(self):
        for problem in Problem.objects.all():
            problem.main_problem_instance.contest = None
            problem.main_problem_instance.round = None
            problem.main_problem_instance.save()

        url = self._get_site_urls()['submissions']
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, '<tr')
        self.assertTrue(self.client.login(username='test_user'))
        self.assertEqual(response.status_code, 200)
        response = self.client.get(url)
        self.assertContains(response, '<tr', count=3)

    def test_submit_tab(self):
        url = reverse('problem_site', kwargs={'site_key': '123'}) + '?key=submit'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(self.client.login(username='test_user'))
        self.assertEqual(response.status_code, 200)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    @override_settings(LANGUAGE_CODE='en')
    def test_settings_tab(self):
        problemsite_url = self._get_site_urls()['statement']
        url = reverse('problem_site', kwargs={'site_key': '123'}) + '?key=settings'

        response = self.client.get(problemsite_url)
        self.assertNotContains(response, 'Settings')

        self.assertTrue(self.client.login(username='test_admin'))
        response = self.client.get(problemsite_url)
        self.assertContains(response, 'Settings')
        response = self.client.get(url)
        self.assertContains(response, 'Add to contest')
        self.assertContains(response, 'Edit problem')
        self.assertContains(response, 'Edit tests')
        self.assertContains(response, 'Reupload problem')
        self.assertContains(response, 'Model solutions')
        self.assertContains(response, 'Medium')

    @override_settings(LANGUAGE_CODE='en')
    def test_tags_tab_admin(self):
        problemsite_url = self._get_site_urls()['statement']
        url = reverse('problem_site', kwargs={'site_key': '123'}) + '?key=tags'

        response = self.client.get(problemsite_url)
        self.assertNotContains(response, 'Tags')

        self.assertTrue(self.client.login(username='test_admin'))
        response = self.client.get(problemsite_url)
        self.assertContains(response, 'Tags')
        response = self.client.get(url)
        self.assertContains(response, 'Current tags')
        self.assertContains(response, 'dp')
        self.assertContains(response, 'lcis')

    @override_settings(LANGUAGE_CODE='en')
    def test_tags_tab_user_with_permission(self):
        problemsite_url = self._get_site_urls()['statement']
        url = reverse('problem_site', kwargs={'site_key': '123'}) + '?key=tags'

        response = self.client.get(problemsite_url)
        self.assertNotContains(response, 'Tags')

        user = User.objects.get(username='test_user')
        permission = Permission.objects.get(codename='can_modify_tags')  
        user.user_permissions.add(permission)

        self.assertTrue(self.client.login(username='test_user'))
        response = self.client.get(problemsite_url)
        self.assertContains(response, 'Tags')
        response = self.client.get(url)
        self.assertContains(response, 'Current tags')
        self.assertContains(response, 'dp')
        self.assertContains(response, 'lcis')

    def test_statement_replacement(self):
        url = (
            reverse('problem_site', kwargs={'site_key': '123'})
            + '?key=replace_problem_statement'
        )

        self.assertTrue(self.client.login(username='test_user'))
        response = self.client.get(url)
        self.assertNotEqual(response.status_code, 200)

        self.assertTrue(self.client.login(username='test_admin'))
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        self.assertContains(response, 'sum_7.pdf')
        new_statement_filename = get_test_filename('blank.pdf')
        response = self.client.post(
            url,
            {
                'file_name': 'sum_7.pdf',
                'file_replacement': open(new_statement_filename, 'rb'),
            },
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'blank.pdf')
        self.assertNotContains(response, 'sum_7.pdf')

        problem = Problem.objects.get(pk=1)
        statement = ProblemStatement.objects.get(problem=problem)
        url = reverse('show_statement', kwargs={'statement_id': statement.id})
        response = self.client.get(url)
        content = self.streamingContent(response)
        self.assertEqual(content, open(new_statement_filename, 'rb').read())

    def test_add_new_tab(self):
        tab_title = 'Test tab'
        tab_contents = 'Hello from test tab'

        @problem_site_tab(tab_title, key='testtab')
        def problem_site_test(request, problem):
            return tab_contents

        url = self._get_site_urls()['site'] + '?key=testtab'
        response = self.client.get(url)
        self.assertContains(response, tab_title)
        self.assertContains(response, tab_contents)

    def test_external_statement_view(self):
        url_external_stmt = reverse(
            'problem_site_external_statement', kwargs={'site_key': '123'}
        )
        response = self.client.get(url_external_stmt)
        self.assertEqual(response.status_code, 200)
        content = self.streamingContent(response)
        self.assertTrue(content.startswith(b'%PDF'))

    def test_external_attachment_view(self):
        self._create_PA()
        url_external_attmt = reverse(
            'problem_site_external_attachment',
            kwargs={'site_key': '123', 'attachment_id': 1},
        )
        response = self.client.get(url_external_attmt)
        self.assertStreamingEqual(response, b'content-of-probatt')

    def test_form_accessibility(self):
        self.assertTrue(self.client.login(username='test_admin'))
        response = self.client.get(self._get_site_urls()['statement'])
        self.assertNotContains(response, 'id="open-form"')

        self.assertTrue(self.client.login(username='test_user'))
        response = self.client.get(self._get_site_urls()['statement'])
        self.assertContains(response, 'id="open-form"')

        self.assertTrue(self.client.login(username='test_user2'))
        response = self.client.get(self._get_site_urls()['statement'])
        self.assertNotContains(response, 'id="open-form"')

        self.assertTrue(self.client.login(username='test_user3'))
        response = self.client.get(self._get_site_urls()['statement'])
        self.assertNotContains(response, 'id="open-form"')


@override_settings(LANGUAGE_CODE="en")
class TestProblemChangeForm(TestCase):
    fixtures = [
        'test_users',
        'test_contest',
        'test_full_package',
        'test_problem_instance',
        'test_quiz_problem_second',
    ]

    def test_programming_problem_change_form(self):
        url = reverse('admin:problems_problem_change', args=(1,))
        response = self.client.get(url, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'Advanced </button>')
        self.assertNotContains(response, 'Tags </button>')
        self.assertNotContains(response, "Problem names")
        self.assertNotContains(response, "Score reveal configs")
        self.assertNotContains(response, "Problem Compilers")

        self.assertTrue(self.client.login(username='test_admin'))
        response = self.client.get(url, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Advanced </button>')
        self.assertContains(response, 'Tags </button>')
        self.assertContains(response, "Problem names")
        self.assertNotContains(response, "Score reveal configs")
        self.assertContains(response, "Problem compilers")
        self.assertNotContains(response, 'None </button>')

    def test_quiz_problem_change_form(self):
        url = reverse('admin:problems_problem_change', args=(101,))
        response = self.client.get(url, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'Advanced </button>')
        self.assertNotContains(response, 'Tags </button>')
        self.assertNotContains(response, "Problem names")
        self.assertNotContains(response, "Quizzes")

        self.assertTrue(self.client.login(username='test_admin'))
        response = self.client.get(url, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Advanced </button>')
        self.assertContains(response, 'Tags </button>')
        self.assertContains(response, "Problem names")
        self.assertContains(response, "Quiz")
        self.assertNotContains(response, 'None </button>')


def get_submission_left(username, contest_id='c', pi_pk=1):
    request = RequestFactory().request()
    request.user = (
        User.objects.get(username=username) if username is not None else AnonymousUser()
    )

    if contest_id is not None:
        request.contest = Contest.objects.get(id=contest_id)
    problem_instance = ProblemInstance.objects.get(pk=pi_pk)
    return problem_instance.controller.get_submissions_left(request, problem_instance)


class TestSubmissionLeft(TestCase):
    fixtures = [
        'test_users',
        'test_contest',
        'test_full_package',
        'test_problem_instance',
        'test_submission',
    ]

    def test_admin(self):
        assert get_submission_left('test_admin') is None

    def test_user_without_submissions(self):
        assert get_submission_left('test_user2') == 10

    def test_user_with_submissions(self):
        assert get_submission_left('test_user') == 9

    def test_not_authenticated_user(self):
        assert get_submission_left(None) is None


class TestSubmissionLeftWhenNoLimit(TestCase):
    fixtures = [
        'test_users',
        'test_contest',
        'test_full_package',
        'test_problem_instance_with_no_submissions_limit',
        'test_submission',
    ]

    def test_admin(self):
        assert get_submission_left('test_admin') is None

    def test_user_without_submissions(self):
        assert get_submission_left('test_user2') is None

    def test_user_with_submissions(self):
        assert get_submission_left('test_user') is None

    def test_not_authenticated_user(self):
        assert get_submission_left(None) is None


class TestSubmissionLeftWhenNoContest(TestCase):
    fixtures = [
        'test_users',
        'test_full_package',
        'test_problem_instance_with_no_contest',
    ]

    def test_admin(self):
        assert get_submission_left('test_admin', None) is None

    def test_user_without_submissions(self):
        assert get_submission_left('test_user', None) is None

    def test_not_authenticated_user(self):
        assert get_submission_left(None, None) is None


class TestProblemSearchPermissions(TestCase, AssertContainsOnlyMixin):
    fixtures = ['test_users', 'test_problem_search_permissions']
    url = reverse('problemset_main')

    task_names = all_values = [
        'Task Public',
        'Task User1Public',
        'Task User1Private',
        'Task Private',
    ]

    def test_search_permissions_public(self):
        self.client.get('/c/c/')
        response = self.client.get(self.url, {'q': 'Task'})
        self.assertEqual(response.status_code, 200)
        self.assert_contains_only(response, ['Task Public', 'Task User1Public'])

        for user in ['test_user', 'test_user2', 'test_admin']:
            self.assertTrue(self.client.login(username=user))
            response = self.client.get(self.url, {'q': 'Task'})
            self.assertEqual(response.status_code, 200)
            self.assert_contains_only(response, ['Task Public', 'Task User1Public'])

    def test_search_permissions_my(self):
        self.assertTrue(self.client.login(username='test_admin'))
        response = self.client.get(self.url + 'myproblems', {'q': 'Task'}, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assert_contains_only(response, [])

        self.assertTrue(self.client.login(username='test_user'))
        response = self.client.get(self.url + 'myproblems', {'q': 'Task'}, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assert_contains_only(response, ['Task User1Public', 'Task User1Private'])

        self.assertTrue(self.client.login(username='test_user2'))
        response = self.client.get(self.url + 'myproblems', {'q': 'Task'}, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assert_contains_only(response, [])

    def test_search_permissions_all(self):
        self.client.get('/c/c/')
        self.assertTrue(self.client.login(username='test_user'))
        response = self.client.get(
            self.url + 'all_problems', {'q': 'Task'}, follow=True
        )
        self.assertEqual(response.status_code, 403)

        hints_url = reverse('get_search_hints', args=('all',))
        response = self.client.get(hints_url, {'q': 'Task'})
        self.assertEqual(response.status_code, 403)

        self.assertTrue(self.client.login(username='test_admin'))
        response = self.client.get(
            self.url + 'all_problems', {'q': 'Task'}, follow=True
        )
        self.assertEqual(response.status_code, 200)
        self.assert_contains_only(response, self.task_names)

        response = self.client.get(hints_url, {'q': 'Task'})
        self.assertEqual(response.status_code, 200)
        self.assert_contains_only(response, self.task_names)


@override_settings(PROBLEM_TAGS_VISIBLE=True)
class TestProblemSearch(TestCase, AssertContainsOnlyMixin):
    fixtures = ['test_problem_search']
    url = reverse('problemset_main')
    task_names = all_values = [
        'Prywatne',
        'Zadanko',
        'Żółć',
        'Znaczn1k',
        'Algorytm',
        'Trudność',
        'Bajtocja',
        'Byteland',
        'Drzewo',
        'Tree',
    ]

    def test_search_name(self):
        self.client.get('/c/c/')
        response = self.client.get(self.url, {'q': 'Zadanko'})
        self.assertEqual(response.status_code, 200)
        self.assert_contains_only(response, ('Zadanko',))

        response = self.client.get(self.url, {'q': 'zADaNkO'})
        self.assertEqual(response.status_code, 200)
        self.assert_contains_only(response, ('Zadanko',))

        response = self.client.get(self.url, {'q': 'zadan'})
        self.assertEqual(response.status_code, 200)
        self.assert_contains_only(response, ('Zadanko',))

    def test_search_name_unicode(self):
        self.client.get('/c/c/')
        response = self.client.get(self.url, {'q': 'Żółć'})
        self.assertEqual(response.status_code, 200)
        self.assert_contains_only(response, ('Żółć',))

        response = self.client.get(self.url, {'q': 'żółć'})
        self.assertEqual(response.status_code, 200)
        self.assert_contains_only(response, ('Żółć',))

        response = self.client.get(self.url, {'q': 'Zolc'})
        self.assertEqual(response.status_code, 200)
        self.assert_contains_only(response, ('Żółć',))

        response = self.client.get(self.url, {'q': 'żoŁc'})
        self.assertEqual(response.status_code, 200)
        self.assert_contains_only(response, ('Żółć',))

        response = self.client.get(self.url, {'q': 'olc'})
        self.assertEqual(response.status_code, 200)
        self.assert_contains_only(response, ('Żółć',))

    def test_search_name_multiple(self):
        self.client.get('/c/c/')
        response = self.client.get(self.url, {'q': 'a'})
        self.assertEqual(response.status_code, 200)
        self.assert_contains_only(
            response, ('Zadanko', 'Znaczn1k', 'Algorytm', 'Byteland')
        )

    def _test_search_name_localized(self, queries, exp_names):
        self.client.get('/c/c/')
        for query, exp_name in zip(queries, exp_names):
            response = self.client.get(self.url, {'q': query})
            self.assertEqual(response.status_code, 200)
            self.assert_contains_only(response, (exp_name,))

    @override_settings(LANGUAGE_CODE="en")
    def test_search_name_localized_en(self):
        queries = 'Byte', 'land', 'bajtocj', 'TrEE', 'RzEw'
        exp_names = 'Byteland', 'Byteland', 'Byteland', 'Tree', 'Tree'
        self._test_search_name_localized(queries, exp_names)

    @override_settings(LANGUAGE_CODE="pl")
    def test_search_name_localized_pl(self):
        queries = 'Bajto', 'baJtOcJ', 'byteland', 'Drzewo', 'tree'
        exp_names = 'Bajtocja', 'Bajtocja', 'Bajtocja', 'Drzewo', 'Drzewo'
        self._test_search_name_localized(queries, exp_names)

    def test_search_short_name(self):
        self.client.get('/c/c/')
        response = self.client.get(self.url, {'q': 'zad'})
        self.assertEqual(response.status_code, 200)
        self.assert_contains_only(response, ('Zadanko',))

        response = self.client.get(self.url, {'q': 'zol'})
        self.assertEqual(response.status_code, 200)
        self.assert_contains_only(response, ('Żółć',))

    def test_search_short_name_multiple(self):
        self.client.get('/c/c/')
        response = self.client.get(self.url, {'q': '1'})
        self.assertEqual(response.status_code, 200)
        self.assert_contains_only(response, ('Zadanko', 'Żółć', 'Znaczn1k'))

    def test_search_tags_basic(self):
        self.client.get('/c/c/')

        response = self.client.get(self.url, {'algorithm': 'tag_a'})
        self.assertEqual(response.status_code, 200)
        self.assert_contains_only(response, ('Algorytm', 'Potagowany'))

        response = self.client.get(self.url, {'difficulty': 'tag_d'})
        self.assertEqual(response.status_code, 200)
        self.assert_contains_only(response, ('Trudność', 'Potagowany'))

        response = self.client.get(
            self.url,
            {
                'algorithm': 'tag_a',
                'difficulty': 'tag_d',
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assert_contains_only(response, ('Potagowany',))

        response = self.client.get(
            self.url,
            {
                'q': 'nic',
                'algorithm': 'tag_a',
                'difficulty': 'tag_d',
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assert_contains_only(response, ())

def problem_name(problem, language):
    problem_name = ProblemName.objects.filter(
        problem=problem, language=language
    ).first()
    return problem_name.name if problem_name else problem.legacy_name

class TestProblemName(TestCase):
    fixtures = ['test_problem_search']

    def test_problem_names(self):
        for (lang_code, _) in settings.LANGUAGES:
            with override_settings(LANGUAGE_CODE=lang_code):
                for problem in Problem.objects.all():
                    self.assertEqual(problem.name, problem_name(problem, lang_code))
