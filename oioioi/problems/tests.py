import urllib

from django.contrib.auth.models import User, Permission
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase, TransactionTestCase
from django.test.utils import override_settings
from django.core.urlresolvers import reverse
from django.core.files.base import ContentFile
from django.http import HttpResponse
from django import forms

from oioioi.base.tests import check_not_accessible
from oioioi.contests.models import Contest, ProblemInstance
from oioioi.filetracker.tests import TestStreamingMixin
from oioioi.problems.controllers import ProblemController
from oioioi.problems.problem_sources import UploadedPackageSource
from oioioi.problems.package import ProblemPackageBackend
from oioioi.problems.models import Problem, ProblemStatement, ProblemPackage, \
        ProblemAttachment, make_problem_filename
from oioioi.problems.problem_site import problem_site_tab
from oioioi.programs.controllers import ProgrammingContestController


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

class TestProblemViews(TestCase, TestStreamingMixin):
    fixtures = ['test_users', 'test_contest', 'test_full_package',
            'test_problem_instance', 'test_permissions']

    def test_problem_statement_view(self):
        #superuser
        self.client.login(username='test_admin')
        statement = ProblemStatement.objects.get()
        url = reverse('show_statement', kwargs={'statement_id': statement.id})
        response = self.client.get(url)
        content = self.streamingContent(response)
        self.assertTrue(content.startswith('%PDF'))
        #contest admin
        self.client.login(username='test_contest_admin')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
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


class DummyPackageException(Exception):
    pass


class DummyPackageBackend(ProblemPackageBackend):
    description = "Dummy Package"

    def identify(self, path, original_filename=None):
        return True

    def get_short_name(self, path, original_filename=None):
        return 'bar'

    def unpack(self, env):
        pp = ProblemPackage.objects.get(id=env['package_id'])
        p = Problem.objects.create(name='foo', short_name='bar',
                controller_name=
                        'oioioi.problems.controllers.ProblemController')
        env['problem_id'] = p.id
        if 'FAIL' in pp.package_file.name:
            raise DummyPackageException("DUMMY_FAILURE")
        return env

    def pack(self, problem):
        return None


def dummy_handler(env):
    pp = ProblemPackage.objects.get(id=env['package_id'])
    if env.get('cc_rulez', False):
        pp.problem_name = 'contest_controller_rulez'
    else:
        pp.problem_name = 'handled'
    pp.save()
    return env


class DummySource(UploadedPackageSource):
    def create_env(self, *args, **kwargs):
        env = super(DummySource, self).create_env(*args, **kwargs)
        env['post_upload_handlers'] += ['oioioi.problems.tests.dummy_handler']
        return env


class DummyContestController(ProgrammingContestController):
    def adjust_upload_form(self, request, existing_problem, form):
        form.fields['cc_rulez'] = forms.BooleanField()

    def fill_upload_environ(self, request, form, env):
        env['cc_rulez'] = form.cleaned_data['cc_rulez']
        env['post_upload_handlers'] += ['oioioi.problems.tests.dummy_handler']


@override_settings(PROBLEM_PACKAGE_BACKENDS=
        ('oioioi.problems.tests.DummyPackageBackend',))
class TestProblemUpload(TransactionTestCase):
    fixtures = ['test_users', 'test_contest']

    def test_successful_upload(self):
        ProblemInstance.objects.all().delete()
        contest = Contest.objects.get()
        self.client.login(username='test_admin')
        data = {'package_file': ContentFile('eloziom', name='foo')}
        url = reverse('oioioi.problems.views.add_or_update_problem_view',
                kwargs={'contest_id': contest.id}) + '?' + \
                        urllib.urlencode({'key': 'upload'})
        response = self.client.post(url, data, follow=True)
        self.assertIn('Package information', response.content)
        self.assertIn('Edit problem', response.content)
        self.assertNotIn('Error details', response.content)
        self.assertNotIn('Model solutions', response.content)
        package = ProblemPackage.objects.get()
        self.assertEqual(package.status, 'OK')
        self.assertEqual(package.problem_name, 'bar')
        problem = Problem.objects.get()
        self.assertEqual(problem.short_name, 'bar')
        problem_instance = ProblemInstance.objects.get()
        self.assertEqual(problem_instance.contest, contest)
        self.assertEqual(problem_instance.problem, problem)

    def test_failed_upload(self):
        ProblemInstance.objects.all().delete()
        contest = Contest.objects.get()
        self.client.login(username='test_admin')
        data = {'package_file': ContentFile('eloziom', name='FAIL')}
        url = reverse('oioioi.problems.views.add_or_update_problem_view',
                kwargs={'contest_id': contest.id}) + '?' + \
                        urllib.urlencode({'key': 'upload'})
        response = self.client.post(url, data, follow=True)
        self.assertIn('DUMMY_FAILURE', response.content)
        self.assertIn('Error details', response.content)
        self.assertNotIn('Edit problem', response.content)
        self.assertNotIn('Model solutions', response.content)
        package = ProblemPackage.objects.get()
        self.assertEqual(package.problem_name, 'bar')
        self.assertEqual(package.status, 'ERR')
        problems = Problem.objects.all()
        self.assertEqual(len(problems), 0)
        problem_instances = ProblemInstance.objects.all()
        self.assertEqual(len(problem_instances), 0)

    @override_settings(PROBLEM_SOURCES=
            ('oioioi.problems.tests.DummySource',))
    def test_handlers(self):
        contest = Contest.objects.get()
        self.client.login(username='test_admin')
        data = {'package_file': ContentFile('eloziom', name='foo')}
        url = reverse('oioioi.problems.views.add_or_update_problem_view',
                kwargs={'contest_id': contest.id}) + '?' + \
                        urllib.urlencode({'key': 'upload'})
        response = self.client.post(url, data, follow=True)
        self.assertIn('Package information', response.content)
        package = ProblemPackage.objects.get()
        self.assertEqual(package.status, 'OK')
        self.assertEqual(package.problem_name, 'handled')

    def test_contest_controller_plugins(self):
        contest = Contest.objects.get()
        contest.controller_name = \
                'oioioi.problems.tests.DummyContestController'
        contest.save()

        self.client.login(username='test_admin')
        data = {'package_file': ContentFile('eloziom', name='foo'),
                'cc_rulez': True}
        url = reverse('oioioi.problems.views.add_or_update_problem_view',
                kwargs={'contest_id': contest.id}) + '?' + \
                        urllib.urlencode({'key': 'upload'})
        response = self.client.post(url, data, follow=True)
        self.assertIn('Package information', response.content)
        package = ProblemPackage.objects.get()
        self.assertEqual(package.status, 'OK')
        self.assertEqual(package.problem_name, 'contest_controller_rulez')

    def test_problem_submission_limit_changed(self):
        contest = Contest.objects.get()
        package_file = ContentFile('eloziom', name='foo')
        self.client.login(username='test_admin')
        url = reverse('oioioiadmin:problems_problem_add')
        response = self.client.get(url, {'contest_id': contest.id},
                follow=True)
        url = response.redirect_chain[-1][0]
        self.assertEqual(response.status_code, 200)

        response = self.client.post(url,
                {'package_file': package_file}, follow=True)
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
                {'package_file': package_file}, follow=True)
        self.assertEqual(response.status_code, 200)

        pis = ProblemInstance.objects.filter(problem=problem)
        self.assertEqual(pis.count(), 1)


class TestProblemPackageAdminView(TestCase):
    fixtures = ['test_users', 'test_contest', 'test_problem_packages',
            'test_problem_instance', 'test_two_empty_contests']

    def test_links(self):
        self.client.login(username='test_admin')
        url = reverse('oioioiadmin:problems_problempackage_changelist')

        self.client.get('/c/c/')  # 'c' becomes the current contest

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertIn('Error details', response.content)
        self.assertIn('Edit problem', response.content)
        self.assertIn('Model solutions', response.content)

        self.client.get('/c/c1/')  # 'c1' becomes the current contest

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertIn('Error details', response.content)
        # Not visible, because the problem's contest is 'c', not 'c1'
        self.assertNotIn('Edit problem', response.content)
        # Not visible, because the problem instances's contest is 'c', not 'c1'
        self.assertNotIn('Model solutions', response.content)


class TestProblemPackageViews(TestCase, TestStreamingMixin):
    fixtures = ['test_users', 'test_contest', 'test_problem_packages',
            'test_problem_instance']

    def _test_package_permissions(self, is_admin=False):
        models = ['problempackage', 'contestproblempackage']
        view_prefix = 'oioioiadmin:problems_'
        package = ProblemPackage.objects.get(pk=2)
        for m in models:
            prefix = view_prefix + m + '_'
            check_not_accessible(self, prefix + 'add')
            check_not_accessible(self, prefix + 'change', args=(package.id,))
            if not is_admin:
                check_not_accessible(self, prefix + 'delete',
                        args=(package.id,))
        if not is_admin:
            check_not_accessible(self,
                    'oioioi.problems.views.download_problem_package_view',
                    args=(package.id,))
            check_not_accessible(self,
                    'oioioi.problems.views.download_package_traceback_view',
                    kwargs={'package_id': str(package.id)})

    def test_admin_changelist_view(self):
        self.client.login(username='test_admin')
        url = reverse('oioioiadmin:problems_problempackage_changelist')
        response = self.client.get(url)
        self.assertContains(response, 'XYZ')

    def test_package_file_view(self):
        package = ProblemPackage.objects.get(pk=1)
        package.package_file = ContentFile('eloziom', name='foo')
        package.save()
        self.client.login(username='test_admin')
        url = reverse('oioioi.problems.views.download_problem_package_view',
                kwargs={'package_id': str(package.id)})
        response = self.client.get(url)
        content = self.streamingContent(response)
        self.assertEqual(content, 'eloziom')

    def test_package_traceback_view(self):
        package = ProblemPackage.objects.get(pk=2)
        package.traceback = ContentFile('eloziom', name='foo')
        package.save()
        self.client.login(username='test_admin')
        url = reverse('oioioi.problems.views.download_package_traceback_view',
                kwargs={'package_id': str(package.id)})
        response = self.client.get(url)
        content = self.streamingContent(response)
        self.assertEqual(content, 'eloziom')

        package.traceback = None
        package.save()
        self.client.login(username='test_admin')
        url = reverse('oioioi.problems.views.download_package_traceback_view',
                kwargs={'package_id': str(package.id)})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_package_permissions(self):
        self._test_package_permissions()
        self.client.login(username='test_user')
        self._test_package_permissions()
        self.client.login(username='test_admin')
        self._test_package_permissions(is_admin=True)


class TestProblemSite(TestCase, TestStreamingMixin):
    fixtures = ['test_users', 'test_contest', 'test_full_package',
            'test_problem_instance', 'test_submission', 'test_problem_site']

    def _get_site_urls(self):
        url = reverse('problem_site', kwargs={'site_key': '123'})
        url_statement = url + "?key=statement"
        url_files = url + "?key=files"
        url_submissions = url + "?key=submissions"
        return {'site': url,
                'statement': url_statement,
                'files': url_files,
                'submissions': url_submissions}

    def _create_PA(self):
        problem = Problem.objects.get()
        pa = ProblemAttachment(problem=problem,
                description='problem-attachment',
                content=ContentFile('content-of-probatt', name='probatt.txt'))
        pa.save()

    def test_default_tabs(self):
        urls = self._get_site_urls()
        response = self.client.get(urls['site'])
        self.assertRedirects(response, urls['statement'])
        response = self.client.get(urls['statement'])
        for url in urls.values():
            self.assertContains(response, url)

    def test_statement_tab(self):
        url_external_stmt = reverse('problem_site_external_statement',
                kwargs={'site_key': '123'})
        response = self.client.get(self._get_site_urls()['statement'])
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, url_external_stmt)

        contest = Contest.objects.get()
        url_submit = reverse('submit', kwargs={'contest_id': contest.id})
        self.assertContains(response, url_submit)

    def test_files_tab(self):
        url = self._get_site_urls()['files']
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content.count('<tr'), 0)

        self._create_PA()

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content.count('<tr'), 2)
        url_attachment = reverse('problem_site_external_attachment',
                kwargs={'site_key': '123', 'attachment_id': 1})
        self.assertContains(response, url_attachment)

    def test_submissions_tab(self):
        url = self._get_site_urls()['submissions']
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content.count('<tr'), 0)
        self.client.login(username='test_user')
        self.assertEqual(response.status_code, 200)
        response = self.client.get(url)
        self.assertEqual(response.content.count('<tr'), 2)

    def test_add_new_tab(self):
        tab_title = 'Test tab'
        tab_contents = 'Hello from test tab'

        @problem_site_tab(tab_title, key='testtab')
        def problem_site_test(request, problem):
            return HttpResponse(tab_contents)

        url = self._get_site_urls()['site'] + '?key=testtab'
        response = self.client.get(url)
        self.assertContains(response, tab_title)
        self.assertContains(response, tab_contents)

    def test_external_statement_view(self):
        url_external_stmt = reverse('problem_site_external_statement',
                kwargs={'site_key': '123'})
        response = self.client.get(url_external_stmt)
        self.assertEqual(response.status_code, 200)
        content = self.streamingContent(response)
        self.assertTrue(content.startswith('%PDF'))

    def test_external_attachment_view(self):
        self._create_PA()
        url_external_attmt = reverse('problem_site_external_attachment',
                kwargs={'site_key': '123', 'attachment_id': 1})
        response = self.client.get(url_external_attmt)
        self.assertStreamingEqual(response, 'content-of-probatt')


class TestProblemsetPage(TestCase):
    fixtures = ['test_users', 'test_problemset_author_problems']

    def test_database(self):
        self.client.login(username='test_user')
        url = reverse('oioioi.problems.views.problemset_main_view')
        response = self.client.post(url)
        public_problems = Problem.objects.filter(is_public=True)
        for problem in public_problems:
            self.assertIn(str(problem.name), str(response.content))

        url = reverse('oioioi.problems.views.problemset_my_problems_view')
        response = self.client.post(url)
        author_user = User.objects.filter(username='test_user')
        author_problems = Problem.objects.filter(author=author_user)
        for problem in author_problems:
            self.assertIn(str(problem.name), str(response.content))
