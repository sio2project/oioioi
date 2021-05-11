# coding: utf-8

import csv
import io
import os.path
import random
from datetime import datetime  # pylint: disable=E0611
from functools import cmp_to_key

import pytest
import six.moves.urllib.parse
from six.moves import range

from django import forms
from django.contrib.auth.models import AnonymousUser, Permission, User
from django.contrib.contenttypes.models import ContentType
from django.core.files.base import ContentFile
from django.db import transaction
from django.test import RequestFactory, TransactionTestCase
from django.test.utils import override_settings
from django.urls import reverse
from django.utils.html import strip_tags
from django.utils.timezone import utc
from oioioi.base.tests import TestCase, check_not_accessible, needs_linux
from oioioi.base.utils.test_migrations import TestCaseMigrations
from oioioi.contests.current_contest import ContestMode
from oioioi.contests.handlers import update_problem_statistics
from oioioi.contests.models import (
    Contest,
    ProblemInstance,
    Round,
    ScoreReport,
    Submission,
    SubmissionReport,
    UserResultForProblem,
)
from oioioi.contests.scores import IntegerScore
from oioioi.filetracker.tests import TestStreamingMixin
from oioioi.problems.controllers import ProblemController
from oioioi.problems.management.commands import (
    create_new_algorithm_tags,
    migrate_old_origin_tags_copy_problem_statements,
    migrate_old_origin_tags_create_new_tags,
    recalculate_statistics,
)
from oioioi.problems.models import (
    AlgorithmTag,
    AlgorithmTagLocalization,
    AlgorithmTagProposal,
    AlgorithmTagThrough,
    DifficultyTag,
    DifficultyTagProposal,
    DifficultyTagThrough,
    OriginInfoCategory,
    OriginInfoCategoryLocalization,
    OriginInfoValue,
    OriginInfoValueLocalization,
    OriginTag,
    OriginTagLocalization,
    Problem,
    ProblemAttachment,
    ProblemPackage,
    ProblemSite,
    ProblemStatement,
    ProblemStatistics,
    Tag,
    TagThrough,
    UserStatistics,
    make_problem_filename,
)
from oioioi.problems.package import ProblemPackageBackend
from oioioi.problems.problem_site import problem_site_tab
from oioioi.problems.problem_sources import UploadedPackageSource
from oioioi.problemsharing.models import Friendship
from oioioi.programs.controllers import ProgrammingContestController


class TestProblemController(ProblemController):
    __test__ = False

    def fill_evaluation_environ(self, environ, submission, **kwargs):
        raise NotImplementedError


class TestModels(TestCase):
    def test_problem_controller_property(self):
        problem = Problem(controller_name='oioioi.problems.tests.TestProblemController')
        self.assertIsInstance(problem.controller, TestProblemController)

    def test_make_problem_filename(self):
        p12 = Problem(pk=12)
        self.assertEqual(make_problem_filename(p12, 'a/hej.txt'), 'problems/12/hej.txt')
        ps = ProblemStatement(pk=22, problem=p12)
        self.assertEqual(make_problem_filename(ps, 'a/hej.txt'), 'problems/12/hej.txt')


class TestProblemViews(TestCase, TestStreamingMixin):
    fixtures = [
        'test_users',
        'test_contest',
        'test_full_package',
        'test_problem_instance',
        'test_permissions',
    ]

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

    def test_admin_delete_view(self):
        self.assertTrue(self.client.login(username='test_admin'))
        problem = Problem.objects.get()
        self.client.get('/c/c/')  # 'c' becomes the current contest
        url = reverse('oioioiadmin:problems_problem_delete', args=(problem.id,))

        self.client.post(url, {'post': 'yes'})
        self.assertEqual(Problem.objects.count(), 0)

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
        p = Problem.create(
            legacy_name='foo',
            short_name='bar',
            controller_name='oioioi.problems.controllers.ProblemController',
        )
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
    fixtures = ['test_users', 'test_contest']

    def test_successful_query(self):
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
        url = reverse('api_package_upload_query')
        data = response.json()
        self.assertTrue('package_id' in data)
        response = self.client.post(url, data, follow=True)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue('package_status' in data)

    def test_failed_query_no_package_id(self):
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
        url = reverse('api_package_upload_query')
        response = self.client.post(url, {}, follow=True)
        self.assertEqual(response.status_code, 400)

    def test_failed_query_no_perm(self):
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
        url = reverse('api_package_upload_query')
        data = response.json()
        response = self.client.post(url, data, follow=True)
        self.assertEqual(response.status_code, 403)


def make_add_update_problem_url(contest, args):
    return '{}?{}'.format(
        reverse('add_or_update_problem', kwargs={'contest_id': contest.id}),
        six.moves.urllib.parse.urlencode(args),
    )


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


class TestProblemPackageAdminView(TestCase):
    fixtures = [
        'test_users',
        'test_contest',
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
        'test_problem_instance',
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
        self.assertContains(response, 'Current tags')
        self.assertContains(response, 'Edit problem')
        self.assertContains(response, 'Edit tests')
        self.assertContains(response, 'Reupload problem')
        self.assertContains(response, 'Model solutions')
        self.assertContains(response, 'dp')
        self.assertContains(response, 'lcis')
        self.assertContains(response, 'Medium')

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


class TestProblemsetPage(TestCase):
    fixtures = ['test_users', 'test_problemset_author_problems', 'test_contest']

    def test_problemlist(self):
        self.assertTrue(self.client.login(username='test_user'))
        url = reverse('problemset_main')
        response = self.client.get(url, follow=True)
        self.assertEqual(response.status_code, 200)
        public_problems = Problem.objects.filter(visibility=Problem.VISIBILITY_PUBLIC)
        for problem in public_problems:
            self.assertContains(response, problem.name)
        # User with no administered contests doesn't see the button
        self.assertNotContains(response, "Add to contest")

        url = reverse('problemset_my_problems')
        response = self.client.get(url, follow=True)
        self.assertEqual(response.status_code, 200)
        author_user = User.objects.filter(username='test_user').get()
        author_problems = Problem.objects.filter(author=author_user)
        for problem in author_problems:
            self.assertContains(response, problem.name)
        # User with no administered contests doesn't see the button
        self.assertNotContains(response, "Add to contest")
        self.assertNotContains(response, 'All problems')

        url = reverse('problemset_all_problems')
        response = self.client.get(url, follow=True)
        self.assertEqual(response.status_code, 403)

        self.assertTrue(self.client.login(username='test_admin'))
        response = self.client.get(url, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'All problems')
        # One link for problem site, another
        # for "More contests..." link in "Actions"
        self.assertContains(
            response, '/problemset/problem/', count=Problem.objects.count() * 2
        )
        self.assertContains(response, 'Add to contest', count=Problem.objects.count())


class TestProblemsharing(TestCase):
    fixtures = ['test_users', 'teachers', 'test_contest']

    def test_shared_with_me_view(self):
        Problem.objects.all().delete()
        Friendship.objects.all().delete()
        ProblemSite.objects.all().delete()
        author_user = User.objects.get(username='test_user')
        teacher = User.objects.get(username='test_user2')
        Problem(
            author=author_user,
            visibility=Problem.VISIBILITY_FRIENDS,
            legacy_name='problem1',
            short_name='prob1',
            controller_name='oioioi.problems.tests.TestProblemController',
        ).save()
        self.assertEqual(Problem.objects.all().count(), 1)
        ProblemSite(
            problem=Problem.objects.get(legacy_name='problem1'),
            url_key='przykladowyurl',
        ).save()
        self.assertEqual(ProblemSite.objects.all().count(), 1)
        Friendship(
            creator=User.objects.get(username='test_user'),
            receiver=User.objects.get(username='test_user2'),
        ).save()
        self.assertEqual(Friendship.objects.all().count(), 1)
        self.assertTrue(self.client.login(username='test_user2'))
        url = reverse('problemset_shared_with_me')
        response = self.client.get(url, follow=True)
        self.assertEqual(response.status_code, 200)
        friends = Friendship.objects.filter(receiver=teacher).values_list(
            'creator', flat=True
        )
        self.assertEqual(friends.count(), 1)
        problems = Problem.objects.filter(
            visibility=Problem.VISIBILITY_FRIENDS,
            author__in=friends,
            problemsite__isnull=False,
        )
        self.assertEqual(problems.count(), 1)
        for problem in problems:
            self.assertContains(response, problem.name)
        # User with no administered contests doesn't see the button
        self.assertNotContains(response, "Add to contest")

    def test_visibility_field_present(self):
        self.assertTrue(self.client.login(username='test_user'))
        url = reverse('problemset_add_or_update')
        response = self.client.get(url, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Visibility")
        self.assertContains(response, "Add problem")

    def test_visibility_default_preference(self):
        Problem.objects.all().delete()
        ProblemSite.objects.all().delete()
        ProblemInstance.objects.all().delete()

        contest = Contest.objects.get()
        self.assertTrue(self.client.login(username='test_admin'))
        url = reverse('oioioiadmin:problems_problem_add')
        response = self.client.get(url, {'contest_id': contest.id}, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.context['form'].initial['visibility'], Problem.VISIBILITY_FRIENDS
        )

        filename = get_test_filename('test_simple_package.zip')
        user = User.objects.filter(username='test_admin').first()
        url = response.redirect_chain[-1][0]
        self.assertIn(
            'problems/add-or-update.html',
            [getattr(t, 'name', None) for t in response.templates],
        )
        response = self.client.post(
            url,
            {
                'package_file': open(filename, 'rb'),
                'visibility': Problem.VISIBILITY_PRIVATE,
                'user': user,
            },
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Problem.objects.count(), 1)
        self.assertEqual(ProblemInstance.objects.count(), 2)

        problem = (
            Problem.objects.filter(contest=contest, author=user).order_by('-id').first()
        )
        self.assertEqual(problem.visibility, Problem.VISIBILITY_PRIVATE)

        # now the last uploaded problem (for this contest)
        # has private visibility, so the form.initial['visibility'] should be set to private too
        url = reverse('oioioiadmin:problems_problem_add')
        response = self.client.get(url, {'contest_id': contest.id}, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.context['form'].initial['visibility'], Problem.VISIBILITY_PRIVATE
        )


def get_test_filename(name):
    return os.path.join(os.path.dirname(__file__), '../sinolpack/files', name)


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
            six.moves.urllib.parse.urlencode({'problem': problem.id}),
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


class TestCreateNewAlgorithmTags(TestCase):
    basedir = os.path.dirname(__file__)
    filename = os.path.join(basedir, 'test_files', 'new_algorithm_tags.csv')

    def setUp(self):
        AlgorithmTag.objects.create(name='unique_tag')

    def tearDown(self):
        AlgorithmTag.objects.all().delete()

    def _test_create_new_algorithm_tags_command(
        self, argv, filename, delete=False, dry_run=False
    ):
        algorithm_tags_count_before = AlgorithmTag.objects.count()
        self.assertTrue(algorithm_tags_count_before, 1)

        manager = create_new_algorithm_tags.Command()
        manager.run_from_argv(argv)

        algorithm_tags_count_after = AlgorithmTag.objects.count()

        with open(filename, mode='r') as csv_file:
            created_algorithm_tags_expected_count = len(csv_file.readlines()) - 1

        if delete:
            if dry_run:
                self.assertEqual(
                    algorithm_tags_count_after, algorithm_tags_count_before
                )
                self.assertTrue(AlgorithmTag.objects.filter(name='unique_tag').exists())
            else:
                self.assertEqual(
                    algorithm_tags_count_after, created_algorithm_tags_expected_count
                )
                self.assertFalse(
                    AlgorithmTag.objects.filter(name='unique_tag').exists()
                )
        else:
            if dry_run:
                self.assertEqual(
                    algorithm_tags_count_after, algorithm_tags_count_before
                )
            else:
                self.assertEqual(
                    algorithm_tags_count_after,
                    algorithm_tags_count_before + created_algorithm_tags_expected_count,
                )
            self.assertTrue(AlgorithmTag.objects.filter(name='unique_tag').exists())

        if not dry_run:
            with open(filename, mode='r') as csv_file:
                csv_reader = csv.DictReader(csv_file, delimiter=',')
                for row in csv_reader:
                    new_tag = AlgorithmTag.objects.get(name=row['name'])
                    new_tag_localizations = AlgorithmTagLocalization.objects.filter(
                        algorithm_tag=new_tag
                    )

                    self.assertEqual(new_tag_localizations.count(), 2)
                    for tag_name in ['full_name_pl', 'full_name_en']:
                        self.assertTrue(
                            new_tag_localizations.filter(
                                full_name=row[tag_name]
                            ).exists()
                        )

    def test_create_new_algorithm_tags_command_with_delete_no_dry_run(self):
        self._test_create_new_algorithm_tags_command(
            [
                'manage.py',
                'create_new_algorithm_tags',
                '--file',
                self.filename,
                '-d',
            ],
            self.filename,
            delete=True,
        )

    def test_create_new_algorithm_tags_command_no_delete_no_dry_run(self):
        self._test_create_new_algorithm_tags_command(
            [
                'manage.py',
                'create_new_algorithm_tags',
                '-f',
                self.filename,
            ],
            self.filename,
        )

    def test_create_new_algorithm_tags_command_no_delete_with_dry_run(self):
        self._test_create_new_algorithm_tags_command(
            [
                'manage.py',
                'create_new_algorithm_tags',
                '-f',
                self.filename,
                '--dry_run',
            ],
            self.filename,
            dry_run=True,
        )

    def test_create_new_algorithm_tags_command_with_delete_with_dry_run(self):
        self._test_create_new_algorithm_tags_command(
            [
                'manage.py',
                'create_new_algorithm_tags',
                '-f',
                self.filename,
                '--delete',
                '-dr',
            ],
            self.filename,
            delete=True,
            dry_run=True,
        )


class TestMigrateOldOriginTagsCreateNewTags(TestCase):
    problems_names = [
        'Kurczak',
        'Herbata',
        'Mleko',
        'Banan',
        'Kanapka',
        'Tost',
        'Ketchup',
        'Pizza',
        'Frytki',
        'Kebab',
        'Piwo',
        'Wino',
        'Czekolada',
        'Kakao',
        'Marchewka',
        'Por',
    ]
    tags_names = [
        'ONTAK2013',
        'ONTAK2012',
        'AMPPZ2012',
        'AMPPZ2011',
        'BOI2015',
        'BOI2008',
        'ILOCAMP11',
        'SERWY2010',
    ]

    def setUp(self):
        for name in self.problems_names:
            Problem.objects.create(
                legacy_name=name,
                short_name=name.lower()[:3],
                visibility='PU',
            )

        Tag.objects.create(name='eng')
        for name in self.tags_names:
            Tag.objects.create(name=name)

        for i, name in enumerate(self.problems_names):
            tag = Tag.objects.get(name=self.tags_names[i % len(self.tags_names)])
            problem = Problem.objects.get(legacy_name=name)
            TagThrough.objects.create(problem=problem, tag=tag)

    def test_migrate_old_origin_tags_create_new_tags_command(self):
        basedir = os.path.dirname(__file__)
        filename = os.path.join(
            basedir, 'test_files', 'old_origin_tags_to_create_tags.csv'
        )
        manager = migrate_old_origin_tags_create_new_tags.Command()
        manager.run_from_argv(
            [
                'manage.py',
                'migrate_old_origin_tags_create_new_tags',
                '-f',
                filename,
            ]
        )

        origin_tag_count = OriginTag.objects.count()
        self.assertEqual(origin_tag_count, 5)
        self.assertEqual(OriginInfoCategory.objects.count(), origin_tag_count)
        self.assertEqual(OriginInfoValue.objects.count(), Tag.objects.count() - 1)

        with open(filename, mode='r') as csv_file:
            csv_reader = csv.DictReader(csv_file, delimiter=',')
            for row in csv_reader:
                old_tags = Tag.objects.filter(name__istartswith=row['OriginTag_name'])
                if row['OriginTag_name'] == 'proserwy':
                    old_tags = Tag.objects.filter(name__istartswith='serwy')
                old_tags_problems = Problem.objects.none()
                for old_tag in old_tags:
                    old_tags_problems |= old_tag.problems.all()
                old_tags_problems_set = set(old_tags_problems)

                origin_tag = OriginTag.objects.get(name=row['OriginTag_name'])
                origin_tag_problems_set = set(origin_tag.problems.all())
                origin_tag_localizations = OriginTagLocalization.objects.filter(
                    origin_tag=origin_tag
                )

                origin_info_category = OriginInfoCategory.objects.get(
                    parent_tag=origin_tag
                )
                origin_info_category_localizations = (
                    OriginInfoCategoryLocalization.objects.filter(
                        origin_info_category=origin_info_category
                    )
                )

                origin_info_value = OriginInfoValue.objects.get(
                    parent_tag=origin_tag,
                    value=row['OriginInfoValue_value'],
                )
                origin_info_value_localizations = (
                    OriginInfoValueLocalization.objects.filter(
                        origin_info_value=origin_info_value
                    )
                )

                self.assertTrue(old_tags_problems_set == origin_tag_problems_set)
                self.assertTrue(len(old_tags_problems_set) in (2, 4))
                self.assertEqual(origin_tag_localizations.count(), 2)
                for tag_name in ['full_name_EN', 'full_name_PL']:
                    colname = 'OriginTagLocalization_' + tag_name
                    self.assertTrue(
                        origin_tag_localizations.filter(full_name=row[colname]).exists()
                    )

                self.assertEqual(origin_info_category.name, 'year')
                self.assertEqual(origin_info_category.order, 1)
                self.assertEqual(origin_info_category_localizations.count(), 2)
                for tag_name in ['full_name_EN', 'full_name_PL']:
                    colname = 'OriginInfoCategoryLocalization_' + tag_name
                    self.assertTrue(
                        origin_info_category_localizations.filter(
                            full_name=row[colname]
                        ).exists()
                    )

                self.assertEqual(int(origin_info_value.value), -origin_info_value.order)
                self.assertEqual(origin_info_value_localizations.count(), 2)
                for tag_name in ['full_value_EN', 'full_value_PL']:
                    colname = 'OriginInfoValueLocalization_' + tag_name
                    self.assertTrue(
                        origin_info_value_localizations.filter(
                            full_value=row[colname]
                        ).exists()
                    )


class TestMigrateOldOriginTagsCopyProblemStatements(TestCase):
    description = {
        'OIG1': {'name_en': 'Kurczak en', 'name_pl': 'Kurczak pl'},
        'IOI2009': {'name_en': 'Herbata en', 'name_pl': 'Herbata pl'},
        'IOI2008': {'name_en': 'Mleko en', 'name_pl': 'Mleko pl'},
        'CEOI2011': {'name_en': 'Banan en', 'name_pl': 'Banan pl'},
        'CEOI2010': {
            'name_en': 'Kanapka en',
            'name_pl': 'Kanapka pl',
        },
        'CEOI2004': {
            'name_en': 'Tost en',
            'name_pl': 'Tost pl',
        },
        'PA2013': {
            'name_en': 'Ketchup en',
            'name_pl': 'Ketchup pl',
        },
        'PA2012': {
            'name_en': 'Pizza en',
            'name_pl': 'Pizza pl',
        },
        'OI21': {
            'name_en': 'Frytki en',
            'name_pl': 'Frytki pl',
        },
        'OI20': {
            'name_en': 'Kebab en',
            'name_pl': 'Kebab pl',
        },
        'OI19': {
            'name_en': 'Piwo en',
            'name_pl': 'Piwo pl',
        },
        'ONTAK2013': {
            'name_en': 'Wino en',
            'name_pl': 'Wino pl',
        },
        'ONTAK2012': {
            'name_en': 'Czekolada en',
            'name_pl': 'Czekolada pl',
        },
        'AMPPZ2012': {
            'name_en': 'Kakao en',
            'name_pl': 'Kakao pl',
        },
        'AMPPZ2011': {
            'name_en': 'Marchewka en',
            'name_pl': 'Marchewka pl',
        },
        'ILOCAMP11': {
            'name_en': 'Por en',
            'name_pl': 'Por pl',
        },
    }

    def setUp(self):
        random.seed(42)
        tag_eng = Tag.objects.create(name='eng')

        for tag_name in self.description:
            tag = Tag.objects.create(name=tag_name)
            problems = self.description[tag_name]

            problem_en = Problem.objects.create(
                legacy_name=problems['name_en'],
                short_name=problems['name_en'].lower()[:3],
                visibility='PU',
            )
            problem_pl = Problem.objects.create(
                legacy_name=problems['name_pl'],
                short_name=problems['name_pl'].lower()[:3],
                visibility='PU',
            )

            if random.choice([True, False]):
                ProblemStatement.objects.create(
                    problem=problem_en,
                    content='data:problems/1/en.pdf:raw:en-pdf',
                )
                ProblemStatement.objects.create(
                    problem=problem_en,
                    content='data:problems/1/en.html:raw:en-html',
                )
                ProblemStatement.objects.create(
                    problem=problem_pl,
                    content='data:problems/1/pl.html:raw:pl-html',
                )
            else:
                ProblemStatement.objects.create(
                    problem=problem_en,
                    language='en',
                    content='data:problems/1/en.html:raw:en-html',
                )
                ProblemStatement.objects.create(
                    problem=problem_pl,
                    language='pl',
                    content='data:problems/1/pl.pdf:raw:pl-pdf',
                )

            TagThrough.objects.create(problem=problem_en, tag=tag_eng)
            TagThrough.objects.create(problem=problem_en, tag=tag)
            TagThrough.objects.create(problem=problem_pl, tag=tag)

    def test_migrate_old_origin_tags_create_copy_problem_statements_command(self):
        problems_count_before = Problem.objects.count()

        basedir = os.path.dirname(__file__)
        filename = os.path.join(
            basedir, 'test_files', 'old_origin_tags_to_copy_statements.csv'
        )
        manager = migrate_old_origin_tags_copy_problem_statements.Command()
        manager.run_from_argv(
            [
                'manage.py',
                'migrate_old_origin_tags_copy_problem_statements',
                '-f',
                filename,
                '-m',
            ]
        )

        self.assertEqual(Problem.objects.count(), problems_count_before)

        tag_copied = Tag.objects.get(name='copied')

        with open(filename, mode='r') as csv_file:
            csv_reader = csv.DictReader(csv_file, delimiter=',')
            for row in csv_reader:
                problems = self.description[row['Tag_name']]
                problem_en = Problem.objects.get(legacy_name=problems['name_en'])
                problem_pl = Problem.objects.get(legacy_name=problems['name_pl'])

                if row['language_version_with_no_origin'] == 'en':
                    self.assertTrue(problem_en in tag_copied.problems.all())

                    problem_en_statement = [
                        problem
                        for problem in ProblemStatement.objects.filter(
                            problem=problem_en
                        )
                        if str(problem.content).endswith('.html')
                    ][0]
                    problem_pl_copied_statement = ProblemStatement.objects.filter(
                        problem=problem_pl, content=problem_en_statement.content
                    ).get()
                    problem_pl_original_statement = (
                        ProblemStatement.objects.filter(problem=problem_pl)
                        .exclude(content=problem_pl_copied_statement.content)
                        .get()
                    )

                    self.assertEqual(problem_pl_copied_statement.language, 'en')
                    self.assertEqual(problem_pl_original_statement.language, 'pl')
                else:
                    self.assertTrue(problem_pl in tag_copied.problems.all())

                    problem_pl_statement = ProblemStatement.objects.filter(
                        problem=problem_pl
                    ).get()
                    problem_en_copied_statement = ProblemStatement.objects.filter(
                        problem=problem_en, content=problem_pl_statement.content
                    ).get()
                    problem_en_original_statements = ProblemStatement.objects.filter(
                        problem=problem_en
                    ).exclude(content=problem_en_copied_statement.content)
                    problem_en_original_statement = [
                        problem
                        for problem in problem_en_original_statements
                        if str(problem.content).endswith('.html')
                    ][0]

                    self.assertEqual(problem_en_copied_statement.language, 'pl')
                    self.assertEqual(problem_en_original_statement.language, 'en')


class TestAlgorithmTagsProposalHintsBase(TestCase):
    """Abstract base class with getting url utility for algorithm tags proposal tests."""

    fixtures = [
        'test_users',
        'test_contest',
        'test_problem_packages',
        'test_problem_site',
        'test_algorithm_tags',
    ]
    view_name = 'get_algorithm_tag_proposal_hints'

    def get_query_url(self, parameters):
        return '{}?{}'.format(
            reverse(self.view_name), six.moves.urllib.parse.urlencode(parameters)
        )


@override_settings(LANGUAGE_CODE='en')
class TestAlgorithmTagsProposalHintsEnglish(TestAlgorithmTagsProposalHintsBase):
    def test_tag_proposal_hints_view(self):
        self.assertTrue(self.client.login(username='test_user'))
        self.client.get('/c/c/')  # 'c' becomes the current contest

        response = self.client.get(self.get_query_url({'query': 'pLeCaK'}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Knapsack problem')
        self.assertNotContains(response, 'Problem plecakowy')
        self.assertNotContains(response, 'pLeCaK')
        self.assertNotContains(response, 'plecak')
        self.assertNotContains(response, 'Longest common increasing subsequence')

        response = self.client.get(self.get_query_url({'query': 'PROBLEM'}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Knapsack problem')
        self.assertNotContains(response, 'Problem plecakowy')
        self.assertNotContains(response, 'Longest common increasing subsequence')

        response = self.client.get(self.get_query_url({'query': 'dynam'}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Dynamic programming')
        self.assertNotContains(response, 'dp')
        self.assertNotContains(response, 'Programowanie dynamiczne')

        response = self.client.get(self.get_query_url({'query': 'greedy'}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Greedy')
        self.assertNotContains(response, 'Dynamic programming')
        self.assertNotContains(response, 'XYZ')

        # Use a byte string in the query to ensure a proper url encoding.
        response = self.client.get(self.get_query_url({'query': 'najdłuższy'}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Longest common increasing subsequence')
        self.assertNotContains(
            response, b'Najd\u0142u\u017cszy wsp\u00f3lny podci\u0105g rosn\u0105cy'
        )
        self.assertNotContains(response, 'lcis')

        response = self.client.get(self.get_query_url({'query': 'l'}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Longest common increasing subsequence')
        self.assertNotContains(
            response, b'Najd\u0142u\u017cszy wsp\u00f3lny podci\u0105g rosn\u0105cy'
        )
        self.assertNotContains(response, 'lcis')
        self.assertNotContains(response, 'Problem plecakowy')


@override_settings(LANGUAGE_CODE='pl')
class TestAlgorithmTagsProposalHintsPolish(TestAlgorithmTagsProposalHintsBase):
    def test_tag_proposal_hints_view(self):
        self.assertTrue(self.client.login(username='test_user'))
        self.client.get('/c/c/')  # 'c' becomes the current contest

        response = self.client.get(self.get_query_url({'query': 'plecak'}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Problem plecakowy')
        self.assertNotContains(response, 'Knapsack problem')
        self.assertNotContains(response, 'Longest common increasing subsequence')

        response = self.client.get(self.get_query_url({'query': 'dynam'}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Programowanie dynamiczne')
        self.assertNotContains(response, 'dp')
        self.assertNotContains(response, 'Dynamic programming')

        response = self.client.get(self.get_query_url({'query': 'greedy'}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, b'Zach\u0142anny')
        self.assertNotContains(response, 'Greedy')

        # Use a byte string in the query to ensure a proper url encoding.
        response = self.client.get(self.get_query_url({'query': 'ZAchłan'}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, b'Zach\u0142anny')
        self.assertNotContains(response, 'Greedy')

        response = self.client.get(self.get_query_url({'query': 'longest'}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response, b'Najd\u0142u\u017cszy wsp\u00f3lny podci\u0105g rosn\u0105cy'
        )
        self.assertNotContains(response, 'Longest common increasing subsequence')
        self.assertNotContains(response, 'lcis')

        response = self.client.get(self.get_query_url({'query': 'lcis'}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response, b'Najd\u0142u\u017cszy wsp\u00f3lny podci\u0105g rosn\u0105cy'
        )
        self.assertNotContains(response, 'Longest common increasing subsequence')
        self.assertNotContains(response, 'lcis')


class TestAlgorithmTagLabel(TestCase):
    fixtures = ['test_algorithm_tags']
    view_name = 'get_algorithm_tag_label'

    def get_tag_labels(self, parameters):
        url = '{}?{}'.format(
            reverse(self.view_name), six.moves.urllib.parse.urlencode(parameters)
        )
        return self.client.get(url)

    def test_algorithm_tag_label_view(self):
        response = self.get_tag_labels(
            {'name': 'Najdłuższy wspólny podciąg rosnący', 'proposed': '-1'}
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response, b'Najd\u0142u\u017cszy wsp\u00f3lny podci\u0105g rosn\u0105cy'
        )

        response = self.get_tag_labels(
            {'name': 'Programowanie dynamiczne', 'proposed': '-1'}
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Programowanie dynamiczne')

        response = self.get_tag_labels({'name': 'Knapsack problem', 'proposed': '-1'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Knapsack problem')

        invalid_query_data = [
            {'name': 'Programowanie dynamiczne', 'proposed': '0'},
            {'name': '', 'proposed': '-1'},
            {'name': 'XYZ', 'proposed': '-1'},
        ]
        for query_data in invalid_query_data:
            response = self.get_tag_labels(query_data)
            self.assertEqual(response.status_code, 404)


class TestSaveProposals(TestCase):
    fixtures = [
        'test_users',
        'test_problem_search',
        'test_algorithm_tags',
        'test_difficulty_tags',
    ]
    url = reverse('save_proposals')

    def test_save_proposals_view(self):
        problem = Problem.objects.get(pk=0)
        user = User.objects.get(username='test_admin')

        self.assertEqual(AlgorithmTagProposal.objects.count(), 0)
        self.assertEqual(DifficultyTagProposal.objects.count(), 0)

        response = self.client.post(
            self.url,
            {
                'tags[]': ["Dynamic programming", "Knapsack problem"],
                'difficulty': '  \r    \t\n        Easy   \n     \t  ',
                'user': 'test_admin',
                'problem': '0',
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(AlgorithmTagProposal.objects.count(), 2)
        self.assertEqual(DifficultyTagProposal.objects.count(), 1)
        self.assertTrue(
            AlgorithmTagProposal.objects.filter(
                problem=problem, tag=AlgorithmTag.objects.get(name='dp'), user=user
            ).exists()
        )
        self.assertTrue(
            AlgorithmTagProposal.objects.filter(
                problem=problem,
                tag=AlgorithmTag.objects.get(name='knapsack'),
                user=user,
            ).exists()
        )
        self.assertTrue(
            DifficultyTagProposal.objects.filter(
                problem=problem, tag=DifficultyTag.objects.get(name='easy'), user=user
            ).exists()
        )

        invalid_query_data = [
            {},
            {
                'difficulty': 'Easy',
                'user': 'test_admin',
                'problem': '0',
            },
            {
                'tags[]': ["Dynamic programming", "Knapsack problem"],
                'user': 'test_admin',
                'problem': '0',
            },
            {
                'tags[]': ["Dynamic programming", "Knapsack problem"],
                'difficulty': 'Easy',
                'problem': '0',
            },
            {
                'tags[]': ["Dynamic programming", "Knapsack problem"],
                'difficulty': 'Easy',
                'user': 'test_admin',
            },
        ]

        for q_data in invalid_query_data:
            response = self.client.post(self.url, q_data)
            self.assertEqual(response.status_code, 400)


class TestNavigationBarItems(TestCase):
    fixtures = ['test_users']

    def test_navigation_bar_items_anonymous(self):
        url_main = reverse('problemset_main')

        response = self.client.get(url_main, follow=True)
        self.assertContains(response, 'Problemset')
        self.assertContains(response, 'Task archive')

    # Regression test for SIO-2278
    @override_settings(CONTEST_MODE=ContestMode.neutral)
    def test_navigation_bar_items_translation(self):
        response = self.client.get(
            reverse('problemset_main'), follow=True, HTTP_ACCEPT_LANGUAGE='en'
        )

        self.assertContains(response, 'Problemset')
        self.assertContains(response, 'Task archive')

        response = self.client.get(
            reverse('problemset_main'), follow=True, HTTP_ACCEPT_LANGUAGE='pl'
        )

        self.assertContains(response, 'Baza zadań')
        self.assertContains(response, 'Archiwum zadań')

    def test_navigation_bar_items_admin(self):
        url_main = reverse('problemset_main')
        url_my = reverse('problemset_my_problems')
        url_all = reverse('problemset_all_problems')
        url_add = reverse('problemset_add_or_update')

        self.assertTrue(self.client.login(username='test_admin'))

        for url in [url_main, url_my, url_all, url_add]:
            response = self.client.get(url, follow=True)
            self.assertContains(response, 'Problemset')
            self.assertContains(response, 'Task archive')


class TestAddToProblemsetPermissions(TestCase):
    fixtures = ['test_users']

    def _assert_can_see_and_add(self):
        url_main = reverse('problemset_main')
        url_add = reverse('problemset_add_or_update')

        response = self.client.get(url_main)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Add problem')
        response = self.client.get(url_add, follow=True)
        self.assertEqual(response.status_code, 200)

    def _assert_can_see_but_cannot_add(self):
        url_main = reverse('problemset_main')
        url_add = reverse('problemset_add_or_update')

        response = self.client.get(url_main, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'Add problem')
        response = self.client.get(url_add, follow=True)
        self.assertEqual(response.status_code, 403)

    @override_settings(EVERYBODY_CAN_ADD_TO_PROBLEMSET=False)
    def test_default_permissions(self):
        self._assert_can_see_but_cannot_add()
        self.assertTrue(self.client.login(username='test_admin'))
        self._assert_can_see_and_add()
        self.assertTrue(self.client.login(username='test_user'))
        self._assert_can_see_but_cannot_add()

    @override_settings(EVERYBODY_CAN_ADD_TO_PROBLEMSET=True)
    def test_everyone_allowed_permissions(self):
        self._assert_can_see_but_cannot_add()
        self.assertTrue(self.client.login(username='test_admin'))
        self._assert_can_see_and_add()
        self.assertTrue(self.client.login(username='test_user'))
        self._assert_can_see_and_add()


class TestAddToContestFromProblemset(TestCase):
    fixtures = [
        'test_users',
        'test_contest',
        'test_full_package',
        'test_problem_instance',
        'test_submission',
        'test_problem_site',
    ]

    def test_add_from_problemlist(self):
        self.assertTrue(self.client.login(username='test_admin'))
        # Visit contest page to register it in recent contests
        contest = Contest.objects.get()
        self.client.get('/c/%s/dashboard/' % contest.id)
        url = reverse('problemset_all_problems')
        response = self.client.get(url, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'All problems')
        # One link for problem site, another
        # for "More contests..." link in "Actions"
        self.assertContains(
            response, '/problemset/problem/', count=Problem.objects.count() * 2
        )
        self.assertContains(response, 'Add to contest', count=Problem.objects.count())
        self.assertContains(response, 'data-addorupdate')
        self.assertContains(response, 'data-urlkey')
        self.assertContains(response, 'add_to_contest')

    def test_add_from_problemsite(self):
        self.assertTrue(self.client.login(username='test_admin'))
        contest = Contest.objects.get()
        self.client.get('/c/%s/dashboard/' % contest.id)
        url = reverse('problem_site', kwargs={'site_key': '123'})
        response = self.client.get(url + '?key=settings', follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Add to contest', count=3)
        self.assertContains(response, 'data-addorupdate')
        self.assertContains(response, 'data-urlkey')
        self.assertContains(response, 'add_to_contest')
        self.assertContains(response, '123')

    def test_add_from_selectcontest(self):
        contest2 = Contest(
            id='c2',
            name='Contest2',
            controller_name='oioioi.contests.tests.PrivateContestController',
        )
        contest2.save()
        contest2.creation_date = datetime(2002, 1, 1, tzinfo=utc)
        contest2.save()
        contest3 = Contest(
            id='c3',
            name='Contest3',
            controller_name='oioioi.contests.tests.PrivateContestController',
        )
        contest3.save()
        contest3.creation_date = datetime(2004, 1, 1, tzinfo=utc)
        contest3.save()
        contest4 = Contest(
            id='c4',
            name='Contest4',
            controller_name='oioioi.contests.tests.PrivateContestController',
        )
        contest4.save()
        contest4.creation_date = datetime(2003, 1, 1, tzinfo=utc)
        contest4.save()

        self.assertTrue(self.client.login(username='test_admin'))
        # Now we're not having any contest in recent contests.
        # As we are contest administrator, the button should still appear.
        url = reverse('problemset_all_problems')
        response = self.client.get(url, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'All problems')
        self.assertContains(
            response, '/problemset/problem/', count=Problem.objects.count() * 2
        )
        self.assertContains(response, 'Add to contest', count=Problem.objects.count())
        # But it shouldn't be able to fill the form
        self.assertNotContains(response, 'data-addorupdate')
        self.assertNotContains(response, 'data-urlkey')
        # And it should point to select_contest page
        self.assertContains(response, '/problem/123/add_to_contest/?problem_name=sum')
        # Follow the link...
        url = reverse('problemset_add_to_contest', kwargs={'site_key': '123'})
        url += '?problem_name=sum'
        response = self.client.get(url, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'to add the <code>sum</code> problem to')
        # This time we should be able to fill the form
        self.assertContains(response, 'data-addorupdate')
        self.assertContains(response, 'data-urlkey')
        self.assertContains(response, 'add_to_contest')
        self.assertContains(response, '123')
        self.assertEqual(len(response.context['administered_contests']), 4)
        self.assertEqual(
            list(response.context['administered_contests']),
            list(Contest.objects.order_by('-creation_date').all()),
        )
        self.assertContains(response, 'Contest2', count=1)
        self.assertContains(response, 'Contest3', count=1)
        self.assertContains(response, 'Contest4', count=1)
        content = response.content.decode('utf-8')
        self.assertLess(content.index('Contest3'), content.index('Contest4'))
        self.assertLess(content.index('Contest4'), content.index('Contest2'))


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


@override_settings(PROBLEM_STATISTICS_AVAILABLE=True)
class TestProblemStatistics(TestCase):
    fixtures = [
        'test_users',
        'test_full_package',
        'test_contest',
        'test_problem_instance',
        'test_extra_contests',
        'test_extra_problem_instance',
        'test_submissions_for_statistics',
        'test_extra_submissions_for_statistics',
    ]

    def test_statistics_updating(self):
        Submission.objects.select_for_update().filter(id__gt=4).update(kind='IGNORED')
        problem = Problem.objects.get(id=1)
        ps, created = ProblemStatistics.objects.get_or_create(problem=problem)
        self.assertTrue(ps.submitted == 0)
        self.assertTrue(ps.solved == 0)
        self.assertTrue(ps.avg_best_score == 0)

        # Count submissions for single user in single problem instance
        # compilation error
        update_problem_statistics({'submission_id': 1})
        ps.refresh_from_db()
        self.assertTrue(ps.submitted == 0)
        self.assertTrue(ps.solved == 0)
        self.assertTrue(ps.avg_best_score == 0)

        # 0 pts
        update_problem_statistics({'submission_id': 2})
        ps.refresh_from_db()
        self.assertTrue(ps.submitted == 1)
        self.assertTrue(ps.solved == 0)
        self.assertTrue(ps.avg_best_score == 0)

        # 42 pts
        update_problem_statistics({'submission_id': 3})
        ps.refresh_from_db()
        self.assertTrue(ps.submitted == 1)
        self.assertTrue(ps.solved == 0)
        self.assertTrue(ps.avg_best_score == 42)

        # 100 pts
        update_problem_statistics({'submission_id': 4})
        ps.refresh_from_db()
        self.assertTrue(ps.submitted == 1)
        self.assertTrue(ps.solved == 1)
        self.assertTrue(ps.avg_best_score == 100)

        # ignore 100 pts
        submission = Submission.objects.select_for_update().get(id=4)
        submission.kind = 'IGNORED'
        submission.save()
        submission.problem_instance.problem.controller.recalculate_statistics_for_user(
            submission.user
        )
        ps.refresh_from_db()
        self.assertTrue(ps.submitted == 1)
        self.assertTrue(ps.solved == 0)
        self.assertTrue(ps.avg_best_score == 42)

        # unignore 100 pts
        submission = Submission.objects.select_for_update().get(id=4)
        submission.kind = 'NORMAL'
        submission.save()
        submission.problem_instance.problem.controller.recalculate_statistics_for_user(
            submission.user
        )
        ps.refresh_from_db()
        self.assertTrue(ps.submitted == 1)
        self.assertTrue(ps.solved == 1)
        self.assertTrue(ps.avg_best_score == 100)

        # delete 100 pts
        submission = Submission.objects.select_for_update().get(id=4).delete()
        ps.refresh_from_db()
        self.assertTrue(ps.submitted == 1)
        self.assertTrue(ps.solved == 0)
        self.assertTrue(ps.avg_best_score == 42)

    def test_statistics_probleminstances(self):
        Submission.objects.select_for_update().filter(id__gt=8).update(kind='IGNORED')

        problem = Problem.objects.get(id=1)
        ps, created = ProblemStatistics.objects.get_or_create(problem=problem)
        self.assertTrue(ps.submitted == 0)
        self.assertTrue(ps.solved == 0)
        self.assertTrue(ps.avg_best_score == 0)

        # Count submissions for two users in two problem instances
        # user1 to pinstance1 100 pts
        update_problem_statistics({'submission_id': 4})
        ps.refresh_from_db()
        self.assertTrue(ps.submitted == 1)
        self.assertTrue(ps.solved == 1)
        self.assertTrue(ps.avg_best_score == 100)

        # user1 to pinstance2 100 pts
        update_problem_statistics({'submission_id': 5})
        ps.refresh_from_db()
        self.assertTrue(ps.submitted == 1)
        self.assertTrue(ps.solved == 1)
        self.assertTrue(ps.avg_best_score == 100)

        # user2 to pinstance1 0 pts
        update_problem_statistics({'submission_id': 6})
        ps.refresh_from_db()
        self.assertTrue(ps.submitted == 2)
        self.assertTrue(ps.solved == 1)
        self.assertTrue(ps.avg_best_score == 50)

        # user2 to pinstance2 50 pts
        update_problem_statistics({'submission_id': 7})
        ps.refresh_from_db()
        self.assertTrue(ps.submitted == 2)
        self.assertTrue(ps.solved == 1)
        self.assertTrue(ps.avg_best_score == 75)

        # user2 to pinstance1 100 pts
        update_problem_statistics({'submission_id': 8})
        ps.refresh_from_db()
        self.assertTrue(ps.submitted == 2)
        self.assertTrue(ps.solved == 2)
        self.assertTrue(ps.avg_best_score == 100)

    def test_recalculate_statistics(self):
        problem = Problem.objects.get(id=1)
        ps, created = ProblemStatistics.objects.get_or_create(problem=problem)
        self.assertTrue(ps.submitted == 0)
        self.assertTrue(ps.solved == 0)
        self.assertTrue(ps.avg_best_score == 0)

        # Best scores for user1: 100, user2: 100, user3: 0, user4: None (CE)
        manager = recalculate_statistics.Command()
        manager.run_from_argv(['manage.py', 'recalculate_statistics'])

        # refresh_from_db() won't work because statistics were deleted
        problem = Problem.objects.get(id=1)
        ps = problem.statistics
        self.assertTrue(ps.submitted == 3)
        self.assertTrue(ps.solved == 2)
        self.assertTrue(ps.avg_best_score == 66)


@override_settings(PROBLEM_STATISTICS_AVAILABLE=True)
class TestProblemStatisticsSpecialCases(TestCase):
    fixtures = [
        'test_users',
        'test_full_package',
        'test_contest',
        'test_problem_instance',
        'test_statistics_special_cases',
    ]

    def test_statistics_null_score(self):
        problem = Problem.objects.get(id=1)
        ps, created = ProblemStatistics.objects.get_or_create(problem=problem)
        self.assertTrue(ps.submitted == 0)
        self.assertTrue(ps.solved == 0)
        self.assertTrue(ps.avg_best_score == 0)

        update_problem_statistics({'submission_id': 10000})
        ps.refresh_from_db()
        self.assertTrue(ps.submitted == 1)
        self.assertTrue(ps.solved == 0)
        self.assertTrue(ps.avg_best_score == 0)

    def test_statistics_zero_max_score(self):
        problem = Problem.objects.get(id=1)
        ps, created = ProblemStatistics.objects.get_or_create(problem=problem)
        self.assertTrue(ps.submitted == 0)
        self.assertTrue(ps.solved == 0)
        self.assertTrue(ps.avg_best_score == 0)

        update_problem_statistics({'submission_id': 10004})
        ps.refresh_from_db()
        self.assertTrue(ps.submitted == 1)
        self.assertTrue(ps.solved == 0)
        self.assertTrue(ps.avg_best_score == 0)

    def test_statistics_weird_scores(self):
        problem = Problem.objects.get(id=1)
        ps, created = ProblemStatistics.objects.get_or_create(problem=problem)
        self.assertTrue(ps.submitted == 0)
        self.assertTrue(ps.solved == 0)
        self.assertTrue(ps.avg_best_score == 0)

        update_problem_statistics({'submission_id': 10002})
        ps.refresh_from_db()
        self.assertTrue(ps.submitted == 1)
        self.assertTrue(ps.solved == 0)
        self.assertTrue(ps.avg_best_score == 50)

        update_problem_statistics({'submission_id': 10003})
        ps.refresh_from_db()
        self.assertTrue(ps.submitted == 1)
        self.assertTrue(ps.solved == 1)
        self.assertTrue(ps.avg_best_score == 100)

    # Check if imported submissions lacking score_report.score and
    # score_report.max_score are handled correctly.
    def test_statistics_imported(self):
        problem = Problem.objects.get(id=1)
        ps, created = ProblemStatistics.objects.get_or_create(problem=problem)
        self.assertTrue(ps.submitted == 0)
        self.assertTrue(ps.solved == 0)
        self.assertTrue(ps.avg_best_score == 0)

        update_problem_statistics({'submission_id': 10001})
        ps.refresh_from_db()
        self.assertTrue(ps.submitted == 1)
        self.assertTrue(ps.solved == 1)
        self.assertTrue(ps.avg_best_score == 100)


@override_settings(PROBLEM_STATISTICS_AVAILABLE=True)
class TestProblemStatisticsDisplay(TestCase):
    fixtures = ['test_users', 'test_statistics_display']

    problem_columns = [
        'short_name',
        'name',
        'submitted',
        'solved_pc',
        'avg_best_score',
        'user_score',
    ]
    problem_data = [
        [u'aaa', u'Aaaa', u'7', u'14%', u'50', None],
        [u'bbb', u'Bbbb', u'8', u'25%', u'45', u'0'],
        [u'ccc', u'Cccc', u'5', u'60%', u'90', u'50'],
        [u'ddd', u'Dddd', u'6', u'66%', u'80', u'90'],
    ]

    def _get_table_contents(self, html):
        col_n = html.count('<th') - html.count('<thead>')
        row_n = html.count('<tr') - 1
        # Skip first `<tr>`
        pos = html.find('<tr') + 1
        self.assertNotEqual(pos, -1)
        rows = []
        for _ in range(row_n):
            pos = html.find('<tr', pos)
            self.assertNotEqual(pos, -1)
            rows.append([])
            for _ in range(col_n):
                pos = html.find('<td', pos)
                self.assertNotEqual(pos, -1)
                none_pos = html.find('<td/>', pos)

                if none_pos == pos:
                    rows[-1].append(None)
                    pos += len('<td/>')
                else:
                    pos2 = html.find('</td>', pos)
                    self.assertNotEqual(pos2, -1)
                    rows[-1].append(strip_tags(html[pos:pos2]).strip())
                    pos = pos2 + len('</td>')
        return rows

    @staticmethod
    def _cmp_str_with_none(key_fn):
        def _cmp(a, b):
            key_a = key_fn(a)
            key_b = key_fn(b)
            if key_a is None:
                return True
            if key_b is None:
                return False
            return key_a < key_b

        return _cmp

    def _assert_rows_sorted(self, rows, order_by=0, desc=False):
        # Nones should be treated as if they were less than zeroes
        # (i.e. listed last when desc=True and listed first otherwise).
        self.assertEqual(
            rows,
            sorted(
                rows,
                key=cmp_to_key(self._cmp_str_with_none(lambda x: x[order_by])),
                reverse=desc,
            ),
        )

    def test_statistics_problem_list(self):
        self.assertTrue(self.client.login(username='test_user'))

        url_main = reverse('problemset_main')
        response = self.client.get(url_main)
        self.assertEqual(response.status_code, 200)

        rows = self._get_table_contents(response.content.decode('utf-8'))
        self.assertEqual(rows, self.problem_data)

        # There are exactly four problems, one for each score class.
        for result in ['result--OK', 'result--TRIED', 'result--FAILED']:
            self.assertContains(response, result, count=1)

    def test_statistics_sorting(self):
        self.assertTrue(self.client.login(username='test_user'))

        for i, column in enumerate(self.problem_columns):
            url_main = reverse('problemset_main')
            response = self.client.get(url_main, {'order_by': column})
            self.assertEqual(response.status_code, 200)

            rows = self._get_table_contents(response.content.decode('utf-8'))
            self._assert_rows_sorted(rows, order_by=i)

            response = self.client.get(url_main, {'order_by': column, 'desc': None})
            self.assertEqual(response.status_code, 200)

            rows = self._get_table_contents(response.content.decode('utf-8'))
            self._assert_rows_sorted(rows, order_by=i, desc=True)

    def test_statistics_nulls(self):
        # Make ccc have null stats
        ProblemStatistics.objects.get(problem__short_name='ccc').delete()

        # Supply user_score for a
        aaa_statistics = UserStatistics(
            problem_statistics=ProblemStatistics.objects.get(problem__short_name='aaa'),
            user=User.objects.get(username='test_user'),
        )
        aaa_statistics.best_score = 0
        aaa_statistics.has_submitted = True
        aaa_statistics.save()

        self.assertTrue(self.client.login(username='test_user'))

        for column in self.problem_columns[2:]:
            url_main = reverse('problemset_main')
            response = self.client.get(url_main, {'order_by': column})
            self.assertEqual(response.status_code, 200)

            rows = self._get_table_contents(response.content.decode('utf-8'))
            self.assertEqual(rows[0], [u'ccc', u'Cccc', '0', None, None, None])

            response = self.client.get(url_main, {'order_by': column, 'desc': None})
            self.assertEqual(response.status_code, 200)

            rows = self._get_table_contents(response.content.decode('utf-8'))
            self.assertEqual(rows[-1], [u'ccc', u'Cccc', '0', None, None, None])

    def test_statistics_sort_nulls(self):
        ProblemStatistics.objects.get(problem__short_name='ccc').delete()

        self.assertTrue(self.client.login(username='test_user'))

        for i, column in enumerate(self.problem_columns):
            url_main = reverse('problemset_main')
            response = self.client.get(url_main, {'order_by': column})
            self.assertEqual(response.status_code, 200)

            rows = self._get_table_contents(response.content.decode('utf-8'))
            self._assert_rows_sorted(rows, order_by=i)

            response = self.client.get(url_main, {'order_by': column, 'desc': None})
            self.assertEqual(response.status_code, 200)

            rows = self._get_table_contents(response.content.decode('utf-8'))
            self._assert_rows_sorted(rows, order_by=i, desc=True)

    # Check that the query and the ordering are correctly preserved in links
    def test_statistics_sorting_with_query(self):
        self.assertTrue(self.client.login(username='test_user'))

        col_no = 3
        q = 'Bbbb'
        order = self.problem_columns[col_no - 1]
        url_main = reverse('problemset_main')

        response = self.client.get(
            url_main, {'q': q, 'foo': 'bar', 'order_by': order, 'desc': None}
        )
        self.assertEqual(response.status_code, 200)

        rows = self._get_table_contents(response.content.decode('utf-8'))
        self.assertEqual(len(rows), 1)

        html = response.content.decode('utf-8')
        pos = html.find('<tr>')
        for _ in range(col_no):
            pos = html.find('<th', pos) + 1
            self.assertNotEqual(pos, -1)
        pos2 = html.find('</th>', pos)
        self.assertNotEqual(pos2, -1)
        th = html[pos:pos2]
        self.assertIn('q=' + q, th)
        self.assertIn('foo=bar', th)
        # The current column link should be to reverse ordering
        self.assertNotIn('desc', th)

        pos = html.find('<th', pos) + 1
        self.assertNotEqual(pos, -1)
        pos2 = html.find('</th>', pos)
        self.assertNotEqual(pos2, -1)
        th = html[pos:pos2]
        self.assertIn('q=' + q, th)
        self.assertIn('foo=bar', th)
        # Any other column links should be to (default) descending ordering
        self.assertIn('desc', th)


@override_settings(PROBLEM_STATISTICS_AVAILABLE=True)
class TestProblemsetFilters(TestCase):
    fixtures = ['test_users', 'test_statistics_display']

    problems = [u'aaa', u'bbb', u'ccc', u'ddd']
    filtered_problems = {
        'all': [u'aaa', u'bbb', u'ccc', u'ddd'],
        'solved': [u'ddd'],
        'attempted': [u'bbb', u'ccc'],
        'not_attempted': [u'aaa'],
    }

    def test_filters(self):
        self.assertTrue(self.client.login(username='test_user'))

        for filter, filtered in self.filtered_problems.items():
            url_main = reverse('problemset_main')
            response = self.client.get(url_main, {'filter': filter})
            self.assertEqual(response.status_code, 200)

            for problem in self.problems:
                if problem in filtered:
                    self.assertContains(response, problem)
                else:
                    self.assertNotContains(response, problem)


@pytest.mark.skip(reason="Migrations have already been applied at the production")
class TestVisibilityMigration(TestCaseMigrations):
    migrate_from = '0013_newtags'
    migrate_to = '0016_visibility_part3'

    def setUpBeforeMigration(self, apps):
        Problem = apps.get_model('problems', 'Problem')
        self.public_problem_id = Problem.objects.create(is_public=True).id
        self.private_problem_id = Problem.objects.create(is_public=False).id

    def test(self):
        self.assertEqual(
            Problem.objects.get(id=self.public_problem_id).visibility,
            Problem.VISIBILITY_PUBLIC,
        )
        self.assertEqual(
            Problem.objects.get(id=self.private_problem_id).visibility,
            Problem.VISIBILITY_FRIENDS,
        )


@pytest.mark.skip(reason="Migrations have already been applied at the production")
class TestVisibilityMigrationReverse(TestCaseMigrations):
    migrate_from = '0016_visibility_part3'
    migrate_to = '0013_newtags'

    def setUpBeforeMigration(self, apps):
        Problem = apps.get_model('problems', 'Problem')
        self.public_problem_id = Problem.objects.create(visibility='PU').id
        self.friends_problem_id = Problem.objects.create(visibility='FR').id
        self.private_problem_id = Problem.objects.create(visibility='PR').id

    def test(self):
        Problem = self.apps.get_model('problems', 'Problem')
        self.assertEqual(Problem.objects.get(id=self.public_problem_id).is_public, True)
        self.assertEqual(
            Problem.objects.get(id=self.friends_problem_id).is_public, False
        )
        self.assertEqual(
            Problem.objects.get(id=self.private_problem_id).is_public, False
        )


class AssertContainsOnlyMixin:
    def assert_contains_only(self, response, allowed_values):
        for task in self.all_values:
            if task in allowed_values:
                self.assertContains(response, task)
            else:
                self.assertNotContains(response, task)


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


class TestProblemSearch(TestCase, AssertContainsOnlyMixin):
    fixtures = ['test_problem_search']
    url = reverse('problemset_main')
    task_names = all_values = [
        'Prywatne',
        'Zadanko',
        'Żółć',
        'Znacznik',
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
            response, ('Zadanko', 'Znacznik', 'Algorytm', 'Byteland')
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
        self.assert_contains_only(response, ('Zadanko', 'Żółć', 'Znacznik'))

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


class TestProblemSearchOrigin(TestCase, AssertContainsOnlyMixin):
    fixtures = ['test_problem_search_origin']
    url = reverse('problemset_main')
    task_names = all_values = [
        '0_private',
        '0_public',
        '1_pa',
        '2_pa_2011',
        '3_pa_2011_r1',
        '3_pa_2011_r2',
        '2_pa_2012',
        '3_pa_2012_r1',
    ]

    def test_search_origintag(self):
        self.client.get('/c/c/')
        response = self.client.get(self.url, {'origin': 'pa'})
        self.assertEqual(response.status_code, 200)
        self.assert_contains_only(response, self.task_names[2:])

        response = self.client.get(self.url, {'origin': ['pa', 'oi']})
        self.assertEqual(response.status_code, 200)
        self.assert_contains_only(response, [])

    def test_search_origininfovalue(self):
        self.client.get('/c/c/')
        response = self.client.get(self.url, {'origin': ['pa_r1']})
        self.assertEqual(response.status_code, 200)
        self.assert_contains_only(response, ['3_pa_2011_r1', '3_pa_2012_r1'])

        response = self.client.get(self.url, {'origin': ['pa', 'pa_r1']})
        self.assertEqual(response.status_code, 200)
        self.assert_contains_only(response, ['3_pa_2011_r1', '3_pa_2012_r1'])

    def test_search_origininfovalue_invalid(self):
        self.client.get('/c/c/')
        response = self.client.get(self.url, {'origin': ['r1']})
        self.assertEqual(response.status_code, 404)

        response = self.client.get(self.url, {'origin': ['pa_2077']})
        self.assertEqual(response.status_code, 404)

        response = self.client.get(self.url, {'origin': ['pa_2011_r1']})
        self.assertEqual(response.status_code, 404)

    def test_search_origininfovalue_multiple(self):
        self.client.get('/c/c/')
        response = self.client.get(self.url, {'origin': ['pa_2011', 'pa_r1']})
        self.assertEqual(response.status_code, 200)
        self.assert_contains_only(response, ['3_pa_2011_r1'])

        response = self.client.get(self.url, {'origin': ['pa_2011', 'pa_r1', 'pa_r2']})
        self.assertEqual(response.status_code, 200)
        self.assert_contains_only(response, ['3_pa_2011_r1', '3_pa_2011_r2'])

        response = self.client.get(self.url, {'origin': ['pa_r1', 'pa_r2']})
        self.assertEqual(response.status_code, 200)
        self.assert_contains_only(
            response, ['3_pa_2011_r1', '3_pa_2011_r2', '3_pa_2012_r1']
        )

        response = self.client.get(
            self.url, {'origin': ['pa_2011', 'pa_2012', 'pa_r1', 'pa_r2']}
        )
        self.assertEqual(response.status_code, 200)
        self.assert_contains_only(
            response, ['3_pa_2011_r1', '3_pa_2011_r2', '3_pa_2012_r1']
        )

        response = self.client.get(self.url, {'origin': ['pa_2012', 'pa_r2']})
        self.assertEqual(response.status_code, 200)
        self.assert_contains_only(response, [])


class TestProblemSearchHintsTags(TestCase, AssertContainsOnlyMixin):
    fixtures = [
        'test_origin_tags',
        'test_algorithm_tags',
        'test_difficulty_tags',
    ]
    url = reverse('get_search_hints', args=('public',))
    category_url = reverse('get_origininfocategory_hints')
    selected_origintag_url = reverse('get_selected_origintag_hints')
    hints = all_values = [
        'very-easy',
        'easy',
        'medium',
        'hard',
        'very-hard',
        'dp',
        'lcis',
        'pa_2011',
        'pa_2012',
        'pa_r1',
        'pa_r2',
        'oi_2011',
        'oi_r1',
        'oi_r2',
        'origintag',
        'round',
        'year',
    ]

    def get_query_url(self, parameters):
        return self.url + '?' + six.moves.urllib.parse.urlencode(parameters)

    @override_settings(LANGUAGE_CODE="en")
    def test_search_hints_tags_basic(self):
        self.client.get('/c/c/')

        response = self.client.get(self.get_query_url({'q': 'najdłuższy'}))
        self.assertEqual(response.status_code, 200)
        self.assert_contains_only(response, ['lcis'])

        response = self.client.get(self.get_query_url({'q': 'easy'}))
        self.assertEqual(response.status_code, 200)
        self.assert_contains_only(response, ['very-easy', 'easy'])

        response = self.client.get(self.get_query_url({'q': 'Mediu'}))
        self.assertEqual(response.status_code, 200)
        self.assert_contains_only(response, ['medium'])

        response = self.client.get(self.get_query_url({'q': 'PROGRA'}))
        self.assertEqual(response.status_code, 200)
        self.assert_contains_only(response, ['dp'])

        response = self.client.get(self.get_query_url({'q': 'dYNAM'}))
        self.assertEqual(response.status_code, 200)
        self.assert_contains_only(response, ['dp'])

        response = self.client.get(self.get_query_url({'q': 'dp'}))
        self.assertEqual(response.status_code, 200)
        self.assert_contains_only(response, [])

        response = self.client.get(self.get_query_url({'q': 'increasing'}))
        self.assertEqual(response.status_code, 200)
        self.assert_contains_only(response, ['lcis'])

    def test_search_hints_origininfo(self):
        self.client.get('/c/c/')
        response = self.client.get(self.url, {'q': 'pa_'})
        self.assertEqual(response.status_code, 200)
        self.assert_contains_only(response, ['pa_2011', 'pa_r1', 'pa_r2'])

        response = self.client.get(self.url, {'q': '2011'})
        self.assertEqual(response.status_code, 200)
        self.assert_contains_only(response, ['pa_2011', 'oi_2011'])

        response = self.client.get(self.url, {'q': 'Round'})
        self.assertEqual(response.status_code, 200)
        self.assert_contains_only(response, ['pa_r1', 'pa_r2', 'oi_r1', 'oi_r2'])

        response = self.client.get(self.url, {'q': 'Potyczki Algorytmiczne'})
        self.assertEqual(response.status_code, 200)
        self.assert_contains_only(response, ['origintag', 'round', 'year'])

    @override_settings(LANGUAGE_CODE="en")
    def test_category_hints(self):
        self.client.get('/c/c/')
        response = self.client.get(
            self.category_url, {'category': 'round', 'q': 'Potyczki Algorytmiczne'}
        )
        self.assertEqual(response.status_code, 200)
        self.assert_contains_only(response, ['pa_r1', 'pa_r2'])

    @override_settings(LANGUAGE_CODE="en")
    def test_selected_origintag_hints_en(self):
        self.client.get('/c/c/')
        response = self.client.get(
            self.selected_origintag_url, {'q': 'Potyczki Algorytmiczne'}
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'pa')
        self.assertContains(response, 'Potyczki Algorytmiczne')
        self.assertContains(response, 'Potyczki Algorytmiczne - Year')
        self.assertContains(response, 'Potyczki Algorytmiczne - Round')
        self.assertNotContains(response, 'Potyczki Algorytmiczne - Rok')
        self.assertNotContains(response, 'Potyczki Algorytmiczne - Runda')
        self.assertNotContains(response, 'pa_r1')
        self.assertNotContains(response, 'pa_r2')
        self.assertNotContains(response, 'pa_2011')
        self.assertNotContains(response, 'pa_2012')

    @override_settings(LANGUAGE_CODE="pl")
    def test_selected_origintag_hints_pl(self):
        self.client.get('/c/c/')
        response = self.client.get(
            self.selected_origintag_url, {'q': 'Potyczki Algorytmiczne'}
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'pa')
        self.assertContains(response, 'Potyczki Algorytmiczne')
        self.assertContains(response, 'Potyczki Algorytmiczne - Rok')
        self.assertContains(response, 'Potyczki Algorytmiczne - Runda')
        self.assertNotContains(response, 'Potyczki Algorytmiczne - Year')
        self.assertNotContains(response, 'Potyczki Algorytmiczne - Round')
        self.assertNotContains(response, 'pa_r1')
        self.assertNotContains(response, 'pa_r2')
        self.assertNotContains(response, 'pa_2011')
        self.assertNotContains(response, 'pa_2012')


@override_settings(LANGUAGE_CODE='pl')
class TestTaskArchive(TestCase):
    fixtures = [
        'test_task_archive',
        'test_users',
        'admin_admin',
        'test_task_archive_progress_labels',
    ]

    def test_unicode_names(self):
        ic = OriginInfoCategory.objects.get(pk=3)
        self.assertEqual(ic.full_name, u"Dzień")
        iv = OriginInfoValue.objects.get(pk=4)
        self.assertEqual(iv.full_name, u"Olimpiada Informatyczna Finał")

    def test_task_archive_main(self):
        response = self.client.get(reverse('task_archive'), follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Olimpiada Informatyczna')
        self.assertContains(response, 'Potyczki Algorytmiczne')

    def test_task_archive_tag(self):
        url = reverse('task_archive_tag', args=('oi',))
        response = self.client.get(url, follow=True)
        self.assertEqual(response.status_code, 200)

        self.assertContains(response, 'Olimpiada Informatyczna')
        self.assertNotContains(response, 'Potyczki Algorytmiczne')
        self.assertContains(response, 'Edycja')
        self.assertContains(response, 'XXIV OI')
        self.assertContains(response, 'XXV OI')
        self.assertContains(response, 'Etap')
        self.assertContains(response, 'Drugi Etap')
        self.assertContains(response, 'Finał')

        self.assertNotContains(response, "alert-warning")
        html = response.content.decode('utf-8')

        pos = html.find('problemgroups')
        self.assertTrue(pos != -1)
        pos = html.find('problemgroups-xxiv', pos)
        self.assertTrue(pos != -1)
        pos = html.find('problemgroups-xxiv-s2', pos)
        self.assertTrue(pos != -1)

        pos1 = html.find('24_s2 1', pos)
        self.assertTrue(pos1 != -1)
        pos2 = html.find('24_s2 2', pos)
        self.assertTrue(pos2 != -1)

        # Test sorting by short names: "24_s2 1" < "24_s2 2"
        self.assertTrue(pos1 < pos2)

        pos = html.find('problemgroups-xxiv-s3', pos)
        self.assertTrue(pos != -1)

        pos1 = html.find('24_s3_d1', pos)
        self.assertTrue(pos1 != -1)
        pos2 = html.find('24_s3_d2', pos)
        self.assertTrue(pos2 != -1)

        # Test sorting by short names: "primary" < "secondary"
        # The short names are such that their alphabetical order does not agree
        # with the names and IDs so that the test is slightly more effective.
        self.assertTrue(pos2 < pos1)

        pos = html.find('problemgroups-xxv', pos)
        self.assertTrue(pos != -1)
        pos = html.find('problemgroups-xxv-s3', pos)
        self.assertTrue(pos != -1)

        pos = html.find('25_s3 1', pos)
        self.assertTrue(pos != -1)
        pos = html.find('25_s3_d2', pos)
        self.assertTrue(pos != -1)

        pos = html.find('</div>', pos)
        self.assertTrue(pos != -1)
        pos = html.find('25 bug', pos)
        self.assertTrue(pos != -1)

        pos = html.find('</div>', pos)
        self.assertTrue(pos != -1)
        pos = html.find('no info', pos)
        self.assertTrue(pos != -1)

        self.assertNotContains(response, 'problemgroups-xxv-s2')
        self.assertNotContains(response, '-d1')
        self.assertNotContains(response, '-d2')

    def test_task_archive_tag_filter(self):
        def assert_problem_found(filters, found=True):
            url = reverse('task_archive_tag', args=('oi',)) + filters
            response = self.client.get(url, follow=True)
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, 'Olimpiada Informatyczna')
            if found:
                self.assertContains(response, '24_s3_d2')
            else:
                self.assertNotContains(response, '24_s3_d2')

        assert_problem_found('')
        assert_problem_found('?edition=xxiv')
        assert_problem_found('?stage=s3')
        assert_problem_found('?edition=xxiv&stage=s3')

        assert_problem_found('?stage=s2', found=False)
        assert_problem_found('?stage=s2&stage=s3')
        assert_problem_found('?edition=xxv', found=False)
        assert_problem_found('?edition=xxiv&edition=xxv')
        assert_problem_found('?stage=s2&edition=xxiv&edition=xxv', found=False)
        assert_problem_found('?stage=s2&stage=s3&edition=xxv', found=False)
        assert_problem_found('?stage=s2&stage=s3&edition=xxiv&edition=xxv')

    def test_task_archive_tag_filter_no_meta_on_problem(self):
        url = reverse('task_archive_tag', args=('oi',)) + '?day=d2'
        response = self.client.get(url, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Olimpiada Informatyczna')

        self.assertContains(response, '24_s3_d2')
        self.assertContains(response, '25_s3_d2')

        self.assertNotContains(response, '24_s2 1')
        self.assertNotContains(response, '24_s2 2')
        self.assertNotContains(response, '24_s3_d1')
        self.assertNotContains(response, '25_s3 1')
        self.assertNotContains(response, '25 bug')
        self.assertNotContains(response, 'no info')

    def test_task_archive_tag_filter_no_meta_on_problem_and_fbclick_tag(self):
        url = reverse('task_archive_tag', args=('oi',)) + '?day=d2&fbclid=a'
        response = self.client.get(url, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Olimpiada Informatyczna')

        self.assertContains(response, '24_s3_d2')
        self.assertContains(response, '25_s3_d2')

        self.assertNotContains(response, '24_s2 1')
        self.assertNotContains(response, '24_s2 2')
        self.assertNotContains(response, '24_s3_d1')
        self.assertNotContains(response, '25_s3 1')
        self.assertNotContains(response, '25 bug')
        self.assertNotContains(response, 'no info')

    def test_task_archive_tag_filter_no_problems(self):
        url = reverse('task_archive_tag', args=('oi',)) + '?stage=1'
        response = self.client.get(url, follow=True)
        self.assertEqual(response.status_code, 200)

        self.assertContains(response, 'Olimpiada Informatyczna')
        self.assertContains(response, "alert-warning")
        self.assertNotContains(response, 'problemgroups')
        self.assertNotContains(response, '24_')
        self.assertNotContains(response, '25_')
        self.assertNotContains(response, '25 bug')
        self.assertNotContains(response, 'no info')

    def test_task_archive_tag_invalid_filter(self):
        url = reverse('task_archive_tag', args=('oi',)) + '?invalid=filter'
        response = self.client.get(url, follow=True)
        self.assertEqual(response.status_code, 404)

    def test_task_archive_tag_fbredirect_filter(self):
        url = reverse('task_archive_tag', args=('oi',)) + '?fbclid=filter'
        response = self.client.get(url, follow=True)
        self.assertEqual(response.status_code, 200)

    def test_task_archive_progress_labels(self):
        url = reverse('task_archive_tag', args=('oi',))

        self.assertTrue(self.client.login(username='test_user'))

        response = self.client.get(url, follow=True)
        self.assertEqual(response.status_code, 200)

        self.assertNotContains(response, "alert-warning")
        self.assertContains(response, "[16.7%]")
        self.assertContains(response, "%", count=1)

        html = response.content.decode('utf-8')

        pos = html.find('label-danger')
        self.assertTrue(pos == -1)
        pos = html.find('label-warning')
        self.assertTrue(pos == -1)
        pos = html.find('<a class="label label-success" href="/s/2/"> 100</a>')
        self.assertTrue(pos != -1)

        self.assertTrue(self.client.login(username='test_user2'))
        response = self.client.get(url, follow=True)
        self.assertEqual(response.status_code, 200)

        self.assertNotContains(response, "alert-warning")
        self.assertContains(response, "[0.0%]")
        self.assertContains(response, "[12.5%]")
        self.assertContains(response, "%", count=2)

        html = response.content.decode('utf-8')

        pos = html.find('<a class="label label-danger" href="/s/3/"> 0</a>')
        self.assertTrue(pos != -1)
        pos = html.find('<a class="label label-warning" href="/s/6/"> 50</a>')
        self.assertTrue(pos != -1)
        pos = html.find('label-success')
        self.assertTrue(pos == -1)

        def test_can_access_with_result(score, max_score):
            user = User.objects.get(username='test_user2')
            problem_instance = ProblemInstance.objects.get(pk=4)
            submission = Submission.objects.create(
                problem_instance=problem_instance, score=score, user=user
            )
            submission_report = SubmissionReport.objects.create(
                kind='NORMAL', submission=submission
            )
            score_report = ScoreReport.objects.create(
                score=score,
                status="OK",
                max_score=max_score,
                submission_report=submission_report,
            )
            user_result = UserResultForProblem.objects.create(
                score=score,
                status='OK',
                user=user,
                submission_report=submission_report,
                problem_instance=problem_instance,
            )

            response = self.client.get(url, follow=True)
            self.assertEqual(response.status_code, 200)

            user_result.delete()
            score_report.delete()
            submission_report.delete()
            submission.delete()

        # we assume that if a max_score exists it never equals zero
        # test_can_access_with_result(IntegerScore(0), IntegerScore(0))
        test_can_access_with_result(None, None)
        test_can_access_with_result(IntegerScore(50), IntegerScore(100))
        test_can_access_with_result(None, IntegerScore(100))
        test_can_access_with_result(IntegerScore(50), None)


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
        self.assertContains(response, "Quizzes")
        self.assertNotContains(response, 'None </button>')
