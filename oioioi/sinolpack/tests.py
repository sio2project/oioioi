# coding: utf-8

import os.path
import zipfile

import pytest
import urllib.parse
from io import BytesIO
from django.conf import settings
from django.core.files import File
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TransactionTestCase
from django.test.utils import override_settings
from django.urls import reverse
from django.utils.html import escape
from django.utils.module_loading import import_string
from oioioi.base.tests import TestCase, needs_linux
from oioioi.contests.current_contest import ContestMode
from oioioi.contests.models import (
    Contest,
    ProblemInstance,
    Submission,
    UserResultForContest,
)
from oioioi.contests.scores import IntegerScore
from oioioi.filetracker.tests import TestStreamingMixin
from oioioi.problems.models import (
    Problem,
    ProblemName,
    ProblemPackage,
    ProblemStatement,
)
from oioioi.problems.package import NoBackend, backend_for_package
from oioioi.programs.models import (
    LanguageOverrideForTest,
    ModelSolution,
    OutputChecker,
    Test,
    TestReport,
)
from oioioi.sinolpack.models import ExtraConfig, ExtraFile
from oioioi.sinolpack.package import (
    DEFAULT_MEMORY_LIMIT,
    DEFAULT_TIME_LIMIT,
    SinolPackageBackend,
)


def get_test_filename(name):
    return os.path.join(os.path.dirname(__file__), 'files', name)


BOTH_CONFIGURATIONS = '%test_both_configurations'


def use_makefiles(fn):
    return override_settings(USE_SINOLPACK_MAKEFILES=True)((fn))


def no_makefiles(fn):
    return override_settings(USE_SINOLPACK_MAKEFILES=False)(fn)


# When a class inheriting from django.test.TestCase is decorated with
# enable_both_unpack_configurations, all its methods decorated with
# both_configurations will be run twice. Once in safe and once in unsafe unpack
# mode.

# Unfortunately, you won't be able run such a decorated method as a single
# test, that is:
# ./test.sh oioioi.sinolpack.tests:TestSinolPackage.test_huge_unpack_update
# will NOT work.
def enable_both_unpack_configurations(cls):
    for name, fn in list(cls.__dict__.items()):
        if getattr(fn, BOTH_CONFIGURATIONS, False):
            setattr(cls, '%s_safe' % (name), no_makefiles(fn))
            setattr(cls, '%s_unsafe' % (name), use_makefiles(fn))
            delattr(cls, name)
    return cls


def both_configurations(fn):
    setattr(fn, BOTH_CONFIGURATIONS, True)
    return fn


class TestSinolPackageIdentify(TestCase):
    def test_identify_zip(self):
        filename = get_test_filename('test_simple_package.zip')
        self.assertTrue(SinolPackageBackend().identify(filename))

    def test_identify_tgz(self):
        filename = get_test_filename('test_full_package.tgz')
        self.assertTrue(SinolPackageBackend().identify(filename))


@enable_both_unpack_configurations
@needs_linux
class TestSinolPackage(TestCase, TestStreamingMixin):
    fixtures = ['test_users', 'test_contest']

    def test_title_in_config_yml(self):
        filename = get_test_filename('test_simple_package.zip')
        call_command('addproblem', filename)
        problem = Problem.objects.get()
        self.assertEqual(problem.name, 'Testowe')

    @override_settings(CONTEST_MODE=ContestMode.neutral)
    def test_single_file_replacement(self):
        filename = get_test_filename('test_simple_package.zip')
        old_statement = 'tst/doc/tstzad.pdf'
        bad_statement = get_test_filename('blank.pdf')
        good_statement = get_test_filename('tstzad.pdf') # copy of blank

        call_command('addproblem', filename)
        problem = Problem.objects.get()
        site_key = problem.problemsite.url_key
        url = (
            reverse('problem_site', kwargs={'site_key': site_key})
            + '?key=manage_files_problem_package'
        )

        self.assertTrue(self.client.login(username='test_user'))
        response = self.client.get(url)
        self.assertNotEqual(response.status_code, 200)

        self.assertTrue(self.client.login(username='test_admin'))
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, old_statement)

        post_data = {
            'file_name': old_statement,
            'file_replacement': open(bad_statement, 'rb'),
            'upload_button': '',
        }
        response = self.client.post(url, post_data, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'must have the same name') # error

        post_data['file_replacement'] = open(good_statement, 'rb')
        response = self.client.post(url, post_data, follow=True)
        self.assertEqual(response.status_code, 200)
        # It is in the old and modified packages' rows and also in a filter
        self.assertContains(response, 'Uploaded', 3)

        statement = ProblemStatement.objects.get(problem=problem)
        url = reverse('show_statement', kwargs={'statement_id': statement.id})
        response = self.client.get(url)
        content = self.streamingContent(response)
        self.assertEqual(content, open(good_statement, 'rb').read())


    def test_title_translations_in_config_yml(self):
        filename = get_test_filename('test_simple_package_translations.zip')
        call_command('addproblem', filename)
        problem = Problem.objects.get()
        problem_names = ProblemName.objects.filter(problem=problem)
        self.assertEqual(problem_names.count(), 2)
        self.assertTrue(
            problem_names.filter(
                name='Problem with translations', language='en'
            ).exists()
        )
        self.assertTrue(
            problem_names.filter(
                name=u'Zadanie z tłumaczeniami', language='pl'
            ).exists()
        )

    def test_title_from_doc(self):
        filename = get_test_filename('test_simple_package_no_config.zip')
        call_command('addproblem', filename)
        problem = Problem.objects.get()
        self.assertNotEqual(problem.name, 'Not this one')
        self.assertEqual(problem.name, 'Testowe')

    def test_latin2_title_from_doc(self):
        filename = get_test_filename('test_simple_package_latin2_title_from_doc.zip')
        call_command('addproblem', filename)
        problem = Problem.objects.get()
        self.assertEqual(problem.name, u'Łąka')

    def test_utf8_title_from_doc(self):
        filename = get_test_filename('test_simple_package_utf8_title_from_doc.zip')
        call_command('addproblem', filename)
        problem = Problem.objects.get()
        self.assertEqual(problem.name, u'Łąka')

    def test_utf8_title_from_config(self):
        filename = get_test_filename('test_simple_package_utf8_title_from_config.zip')
        call_command('addproblem', filename)
        problem = Problem.objects.get()
        self.assertEqual(problem.name, u'ĄąĆćĘęŁłÓóŚśŻżŹź')

    def test_memory_limit_from_doc(self):
        filename = get_test_filename('test_simple_package_no_config.zip')
        call_command('addproblem', filename)
        test = Test.objects.filter(memory_limit=132000)
        self.assertEqual(test.count(), 5)

    def test_attachments(self):
        filename = get_test_filename('test_simple_package_attachments.zip')
        call_command('addproblem', filename)
        problem = Problem.objects.get()
        self.assertEqual(problem.attachments.all().count(), 1)

    def test_attachments_no_directory(self):
        filename = get_test_filename('test_simple_package.zip')
        call_command('addproblem', filename)
        problem = Problem.objects.get()
        self.assertEqual(problem.attachments.all().count(), 0)

    def test_attachments_empty_directory(self):
        filename = get_test_filename('test_simple_package_attachments_empty.zip')
        call_command('addproblem', filename)
        problem = Problem.objects.get()
        self.assertEqual(problem.attachments.all().count(), 0)

    def test_attachments_reupload_same_attachments(self):
        filename = get_test_filename('test_simple_package_attachments.zip')
        call_command('addproblem', filename)
        problem = Problem.objects.get()

        filename = get_test_filename('test_simple_package_attachments.zip')
        call_command('updateproblem', str(problem.id), filename)
        problem = Problem.objects.get()
        self.assertEqual(problem.attachments.all().count(), 1)

    def test_attachments_reupload_no_attachments(self):
        filename = get_test_filename('test_simple_package_attachments.zip')
        call_command('addproblem', filename)
        problem = Problem.objects.get()

        filename = get_test_filename('test_simple_package_attachments_empty.zip')
        call_command('updateproblem', str(problem.id), filename)
        problem = Problem.objects.get()
        self.assertEqual(problem.attachments.all().count(), 0)

    def test_assign_points_from_file(self):
        filename = get_test_filename('test_scores.zip')
        call_command('addproblem', filename)
        problem = Problem.objects.get()

        tests = Test.objects.filter(problem_instance=problem.main_problem_instance)

        self.assertEqual(tests.get(name='1a').max_score, 42)
        self.assertEqual(tests.get(name='1b').max_score, 42)
        self.assertEqual(tests.get(name='1c').max_score, 42)
        self.assertEqual(tests.get(name='2').max_score, 23)

    def test_assign_global_time_limit_from_file(self):
        filename = get_test_filename('test_global_time_limit.zip')
        call_command('addproblem', filename)
        problem = Problem.objects.get()

        tests = Test.objects.filter(problem_instance=problem.main_problem_instance)

        self.assertEqual(tests.get(name='1a').time_limit, 7000)
        self.assertEqual(tests.get(name='1b').time_limit, 7000)
        self.assertEqual(tests.get(name='1c').time_limit, 7000)
        self.assertEqual(tests.get(name='2').time_limit, 7000)

    def test_assign_time_limits_for_groups_from_file(self):
        filename = get_test_filename('test_time_limits_for_group.zip')
        call_command('addproblem', filename)
        problem = Problem.objects.get()

        tests = Test.objects.filter(problem_instance=problem.main_problem_instance)

        self.assertEqual(tests.get(name='1a').time_limit, 2000)
        self.assertEqual(tests.get(name='1b').time_limit, 2000)
        self.assertEqual(tests.get(name='1c').time_limit, 2000)
        self.assertEqual(tests.get(name='2').time_limit, 3000)

    @pytest.mark.xfail(strict=True)
    def test_assign_time_limits_for_groups_nonexistent(self):
        filename = get_test_filename('test_time_limits_for_nonexisting_group.zip')
        self.assertRaises(CommandError, call_command, 'addproblem', filename)
        call_command('addproblem', filename, "nothrow")
        self.assertEqual(Problem.objects.count(), 0)
        package = ProblemPackage.objects.get()
        self.assertEqual(package.status, "ERR")
        # Check if error message is relevant to the issue
        self.assertIn("no such test group exists", package.info)

    def test_assign_time_limits_for_different_levels(self):
        filename = get_test_filename('test_time_limit_levels.zip')
        call_command('addproblem', filename)
        problem = Problem.objects.get()

        tests = Test.objects.filter(problem_instance=problem.main_problem_instance)

        self.assertEqual(tests.get(name='1a').time_limit, 3000)
        self.assertEqual(tests.get(name='1b').time_limit, 5000)
        self.assertEqual(tests.get(name='1c').time_limit, 5000)
        self.assertEqual(tests.get(name='2').time_limit, 7000)

    def test_assign_points_nonexistent(self):
        filename = get_test_filename('test_scores_nonexistent_fail.zip')
        self.assertRaises(CommandError, call_command, 'addproblem', filename)
        call_command('addproblem', filename, "nothrow")
        self.assertEqual(Problem.objects.count(), 0)
        package = ProblemPackage.objects.get()
        self.assertEqual(package.status, "ERR")
        # Check if error message is relevant to the issue
        self.assertIn("no such test group exists", package.info)

    def test_assign_points_not_exhaustive(self):
        filename = get_test_filename('test_scores_notexhaustive_fail.zip')
        self.assertRaises(CommandError, call_command, 'addproblem', filename)
        call_command('addproblem', filename, "nothrow")
        self.assertEqual(Problem.objects.count(), 0)
        package = ProblemPackage.objects.get()
        self.assertEqual(package.status, "ERR")
        # Check if error message is relevant to the issue
        self.assertIn("Score for group", package.info)
        self.assertIn("not found", package.info)

    @pytest.mark.slow
    @both_configurations
    @override_settings(CONTEST_MODE=ContestMode.neutral)
    def test_huge_unpack_update(self):
        self.assertTrue(self.client.login(username='test_admin'))
        filename = get_test_filename('test_huge_package.tgz')
        call_command('addproblem', filename)
        problem = Problem.objects.get()

        # Rudimentary test of package updating
        url = (
            reverse('add_or_update_problem')
            + '?'
            + urllib.parse.urlencode({'problem': problem.id})
        )
        response = self.client.get(url, follow=True)
        self.assertEqual(response.status_code, 200)
        url = response.redirect_chain[-1][0]
        response = self.client.post(
            url,
            {
                'package_file': open(filename, 'rb'),
                'visibility': Problem.VISIBILITY_PRIVATE,
            },
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        url = reverse('oioioiadmin:problems_problempackage_changelist')
        self.assertRedirects(response, url)

    def _check_no_ingen_package(self, problem, doc=True):
        self.assertEqual(problem.short_name, 'test')

        tests = Test.objects.filter(problem_instance=problem.main_problem_instance)
        t0 = tests.get(name='0')
        self.assertEqual(t0.input_file.read(), b'0 0\n')
        self.assertEqual(t0.output_file.read(), b'0\n')
        self.assertEqual(t0.kind, 'EXAMPLE')
        self.assertEqual(t0.group, '0')
        self.assertEqual(t0.max_score, 0)
        self.assertEqual(t0.time_limit, DEFAULT_TIME_LIMIT)
        self.assertEqual(t0.memory_limit, DEFAULT_MEMORY_LIMIT)
        t1a = tests.get(name='1a')
        self.assertEqual(t1a.input_file.read(), b'0 0\n')
        self.assertEqual(t1a.output_file.read(), b'0\n')
        self.assertEqual(t1a.kind, 'NORMAL')
        self.assertEqual(t1a.group, '1')
        self.assertEqual(t1a.max_score, 100)
        self.assertEqual(t1a.time_limit, DEFAULT_TIME_LIMIT)
        self.assertEqual(t1a.memory_limit, DEFAULT_MEMORY_LIMIT)
        t1b = tests.get(name='1b')
        self.assertEqual(t1b.input_file.read(), b'0 0\n')
        self.assertEqual(t1b.output_file.read(), b'0\n')
        self.assertEqual(t1b.kind, 'NORMAL')
        self.assertEqual(t1b.group, '1')
        self.assertEqual(t1b.max_score, 100)
        self.assertEqual(t1b.time_limit, DEFAULT_TIME_LIMIT)
        self.assertEqual(t1b.memory_limit, DEFAULT_MEMORY_LIMIT)

        model_solutions = ModelSolution.objects.filter(problem=problem)
        sol = model_solutions.get(name='test.c')
        self.assertEqual(sol.kind, 'NORMAL')
        self.assertEqual(model_solutions.count(), 1)

    @both_configurations
    def test_no_ingen_package(self):
        filename = get_test_filename('test_no_ingen_package.tgz')
        call_command('addproblem', filename)
        problem = Problem.objects.get()
        self._check_no_ingen_package(problem)

        # Rudimentary test of package updating
        call_command('updateproblem', str(problem.id), filename)
        problem = Problem.objects.get()
        self._check_no_ingen_package(problem)

    def _check_full_package(self, problem, doc=True):
        self.assertEqual(problem.short_name, 'sum')

        config = ExtraConfig.objects.get(problem=problem)
        assert 'extra_compilation_args' in config.parsed_config

        if doc:
            self.assertEqual(problem.name, u'Sumżyce')
            if settings.USE_SINOLPACK_MAKEFILES:
                statements = ProblemStatement.objects.filter(problem=problem)
                self.assertEqual(statements.count(), 1)
                self.assertTrue(statements.get().content.read().startswith(b'%PDF'))
        else:
            self.assertEqual(problem.name, u'sum')

        tests = Test.objects.filter(problem_instance=problem.main_problem_instance)
        t0 = tests.get(name='0')
        self.assertEqual(t0.input_file.read(), b'1 2\n')
        self.assertEqual(t0.output_file.read(), b'3\n')
        self.assertEqual(t0.kind, 'EXAMPLE')
        self.assertEqual(t0.group, '0')
        self.assertEqual(t0.max_score, 0)
        self.assertEqual(t0.time_limit, DEFAULT_TIME_LIMIT)
        self.assertEqual(t0.memory_limit, 133000)
        t1a = tests.get(name='1a')
        self.assertEqual(t1a.kind, 'NORMAL')
        self.assertEqual(t1a.group, '1')
        self.assertEqual(t1a.max_score, 33)
        t1b = tests.get(name='1b')
        self.assertEqual(t1b.kind, 'NORMAL')
        self.assertEqual(t1b.group, '1')
        self.assertEqual(t1b.max_score, 33)
        self.assertEqual(t1b.time_limit, 100)
        t1ocen = tests.get(name='1ocen')
        self.assertEqual(t1ocen.kind, 'EXAMPLE')
        self.assertEqual(t1ocen.group, '1ocen')
        self.assertEqual(t1ocen.max_score, 0)
        t2 = tests.get(name='2')
        self.assertEqual(t2.kind, 'NORMAL')
        self.assertEqual(t2.group, '2')
        self.assertEqual(t2.max_score, 33)
        t3 = tests.get(name='3')
        self.assertEqual(t3.kind, 'NORMAL')
        self.assertEqual(t3.group, '3')
        self.assertEqual(t3.max_score, 34)
        self.assertEqual(tests.count(), 6)

        checker = OutputChecker.objects.get(problem=problem)
        self.assertTrue(bool(checker.exe_file))

        extra_files = ExtraFile.objects.filter(problem=problem)
        self.assertEqual(extra_files.count(), 1)
        self.assertEqual(extra_files.get().name, 'makra.h')

        model_solutions = ModelSolution.objects.filter(problem=problem).order_by(
            'order_key'
        )
        sol = model_solutions.get(name='sum.c')
        self.assertEqual(sol.kind, 'NORMAL')
        sol1 = model_solutions.get(name='sums1.cpp')
        self.assertEqual(sol1.kind, 'SLOW')
        solb0 = model_solutions.get(name='sumb0.c')
        self.assertEqual(solb0.kind, 'INCORRECT')
        self.assertEqual(model_solutions.count(), 3)
        self.assertEqual(list(model_solutions), [sol, sol1, solb0])

        tests = Test.objects.filter(problem_instance=problem.main_problem_instance)

    @pytest.mark.slow
    @both_configurations
    def test_full_unpack_update(self):
        filename = get_test_filename('test_full_package.tgz')
        call_command('addproblem', filename)
        problem = Problem.objects.get()
        self._check_full_package(problem)

        # Rudimentary test of package updating
        call_command('updateproblem', str(problem.id), filename)
        problem = Problem.objects.get()
        self._check_full_package(problem)

    def _check_interactive_package(self, problem):
        self.assertEqual(problem.short_name, 'arc')

        config = ExtraConfig.objects.get(problem=problem)
        assert len(config.parsed_config['extra_compilation_args']) == 2
        assert len(config.parsed_config['extra_compilation_files']) == 2

        self.assertEqual(problem.name, u'arc')

        tests = Test.objects.filter(problem_instance=problem.main_problem_instance)

        t0 = tests.get(name='0')
        self.assertEqual(t0.input_file.read(), b'3\n12\n5\n8\n3\n15\n8\n0\n')
        self.assertEqual(t0.output_file.read(), b'12\n15\n8\n')
        self.assertEqual(t0.kind, 'EXAMPLE')
        self.assertEqual(t0.group, '0')
        self.assertEqual(t0.max_score, 0)
        self.assertEqual(t0.time_limit, DEFAULT_TIME_LIMIT)
        self.assertEqual(t0.memory_limit, 66000)
        t1a = tests.get(name='1a')
        self.assertEqual(
            t1a.input_file.read(), b'0\n-435634223 1 30 23 130 0 -324556462\n'
        )
        self.assertEqual(
            t1a.output_file.read(),
            b"""126\n126\n82\n85\n80\n64\n84\n5\n128\n66\n4\n79\n64\n96
22\n107\n84\n112\n92\n63\n125\n82\n1\n""",
        )
        self.assertEqual(t1a.kind, 'NORMAL')
        self.assertEqual(t1a.group, '1')
        self.assertEqual(t1a.max_score, 50)
        t2a = tests.get(name='2a')
        self.assertEqual(
            t2a.input_file.read(), b'0\n-435634223 1 14045 547 60000 0 -324556462\n'
        )
        self.assertEqual(t2a.kind, 'NORMAL')
        self.assertEqual(t2a.group, '2')
        self.assertEqual(t2a.max_score, 50)

        checker = OutputChecker.objects.get(problem=problem)
        self.assertIsNotNone(checker.exe_file)

        extra_files = ExtraFile.objects.filter(problem=problem)
        self.assertEqual(extra_files.count(), 2)

        model_solutions = ModelSolution.objects.filter(problem=problem).order_by(
            'order_key'
        )
        solc = model_solutions.get(name='arc.c')
        self.assertEqual(solc.kind, 'NORMAL')
        solcpp = model_solutions.get(name='arc1.cpp')
        self.assertEqual(solcpp.kind, 'NORMAL')
        self.assertEqual(list(model_solutions), [solc, solcpp])

        submissions = Submission.objects.all()
        for s in submissions:
            self.assertEqual(s.status, 'INI_OK')
            self.assertEqual(s.score, IntegerScore(100))

    @pytest.mark.slow
    @both_configurations
    def test_interactive_task(self):
        filename = get_test_filename('test_interactive_package.tgz')
        call_command('addproblem', filename)
        problem = Problem.objects.get()
        self._check_interactive_package(problem)

    def _add_problem_with_author(self, filename, author, nothrow=False):
        try:
            backend = import_string(backend_for_package(filename))()
        except NoBackend:
            raise ValueError("Package format not recognized")

        pp = ProblemPackage(problem=None)
        pp.package_file.save(filename, File(open(filename, 'rb')))
        env = {'author': author}
        pp.problem_name = backend.get_short_name(filename)
        pp.save()

        env['package_id'] = pp.id
        problem = None
        with pp.save_operation_status():
            backend.unpack(env)
            problem = Problem.objects.get(id=env['problem_id'])
            pp.problem = problem
            pp.save()

        if problem is None and not nothrow:
            raise ValueError("Error during unpacking the given package")

    def test_restrict_html(self):
        self.assertTrue(self.client.login(username='test_user'))
        filename = get_test_filename(
            'test_simple_package_with_malicious_html_statement.zip'
        )

        with self.settings(USE_SINOLPACK_MAKEFILES=False):
            with self.settings(SINOLPACK_RESTRICT_HTML=True):
                self._add_problem_with_author(filename, 'test_user', True)
                self.assertEqual(Problem.objects.count(), 0)
                package = ProblemPackage.objects.get()
                self.assertEqual(package.status, "ERR")
                # Check if error message is relevant to the issue
                self.assertIn("problem statement in HTML", package.info)

                self._add_problem_with_author(filename, 'test_admin')

        self._add_problem_with_author(filename, 'test_user')

        with self.settings(SINOLPACK_RESTRICT_HTML=True):
            self._add_problem_with_author(filename, 'test_user')

        self.assertEqual(Problem.objects.count(), 3)

    @pytest.mark.slow
    @both_configurations
    def test_overriden_limits(self):
        filename = get_test_filename('test_limits_overriden_for_cpp.zip')
        call_command('addproblem', filename)
        problem = Problem.objects.get()
        tests = Test.objects.filter(problem_instance=problem.main_problem_instance)
        overriden_tests = LanguageOverrideForTest.objects.filter(test__in=tests)
        self.assertTrue(len(overriden_tests) > 0)
        self.assertTrue(all([t.language == 'cpp' for t in overriden_tests]))
        # New global time limit
        self.assertTrue(all([t.time_limit == 1000 for t in overriden_tests]))

        overriden_memory_group = overriden_tests.filter(test__group=1)
        self.assertTrue(all([t.memory_limit == 6000 for t in overriden_memory_group]))
        overriden_memory_group2 = overriden_tests.filter(test__group=2)
        self.assertTrue(all([t.memory_limit == 2000 for t in overriden_memory_group2]))


@enable_both_unpack_configurations
@needs_linux
class TestSinolPackageInContest(TransactionTestCase, TestStreamingMixin):
    fixtures = ['test_users', 'test_contest']

    @both_configurations
    def test_upload_and_download_package(self):
        ProblemInstance.objects.all().delete()

        contest = Contest.objects.get()
        contest.default_submissions_limit = 123
        contest.save()

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
        response = self.client.post(
            url,
            {
                'package_file': open(filename, 'rb'),
                'visibility': Problem.VISIBILITY_PRIVATE,
            },
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Problem.objects.count(), 1)
        self.assertEqual(ProblemInstance.objects.count(), 2)
        self.assertEqual(
            ProblemInstance.objects.get(contest=contest).submissions_limit, 123
        )

        contest.default_submissions_limit = 124
        contest.save()

        # Delete tests and check if re-uploading will fix it.
        problem = Problem.objects.get()
        problem_instance = ProblemInstance.objects.filter(contest__isnull=False).get()
        num_tests = problem_instance.test_set.count()
        for test in problem_instance.test_set.all():
            test.delete()
        problem_instance.save()
        # problem instances are independent
        problem_instance = problem.main_problem_instance
        self.assertEqual(problem_instance.test_set.count(), num_tests)
        num_tests = problem_instance.test_set.count()
        for test in problem_instance.test_set.all():
            test.delete()
        problem_instance.save()

        url = (
            reverse('add_or_update_problem', kwargs={'contest_id': contest.id})
            + '?'
            + urllib.parse.urlencode({'problem': problem_instance.problem.id})
        )
        response = self.client.get(url, follow=True)
        url = response.redirect_chain[-1][0]
        self.assertEqual(response.status_code, 200)
        self.assertIn(
            'problems/add-or-update.html',
            [getattr(t, 'name', None) for t in response.templates],
        )
        response = self.client.post(
            url,
            {
                'package_file': open(filename, 'rb'),
                'visibility': Problem.VISIBILITY_PRIVATE,
            },
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        problem_instance = ProblemInstance.objects.filter(contest__isnull=False).get()
        self.assertEqual(problem_instance.test_set.count(), num_tests)
        self.assertEqual(problem_instance.submissions_limit, 123)
        problem_instance = problem.main_problem_instance
        self.assertEqual(problem_instance.test_set.count(), num_tests)

        response = self.client.get(
            reverse(
                'oioioiadmin:problems_problem_download',
                args=(problem_instance.problem.id,),
            )
        )
        self.assertStreamingEqual(response, open(filename, 'rb').read())

    @both_configurations
    def test_inwer_failure_package(self):
        ProblemInstance.objects.all().delete()

        contest = Contest.objects.get()
        filename = get_test_filename('test_inwer_failure.zip')
        self.assertTrue(self.client.login(username='test_admin'))
        url = reverse('oioioiadmin:problems_problem_add')
        response = self.client.get(url, {'contest_id': contest.id}, follow=True)
        url = response.redirect_chain[-1][0]
        self.assertEqual(response.status_code, 200)
        response = self.client.post(
            url,
            {
                'package_file': open(filename, 'rb'),
                'visibility': Problem.VISIBILITY_PRIVATE,
            },
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Problem.objects.count(), 0)
        self.assertEqual(ProblemInstance.objects.count(), 0)
        self.assertEqual(ProblemPackage.objects.count(), 0)


class TestSinolPackageCreator(TestCase, TestStreamingMixin):
    fixtures = [
        'test_users',
        'test_full_package',
        'test_problem_instance_with_no_contest',
    ]

    def test_sinol_package_creator(self):
        problem = Problem.objects.get()
        self.assertTrue(self.client.login(username='test_admin'))
        response = self.client.get(
            reverse('oioioiadmin:problems_problem_download', args=(problem.id,))
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/zip')
        stream = BytesIO(self.streamingContent(response))
        zip = zipfile.ZipFile(stream, 'r')
        self.assertEqual(
            sorted(zip.namelist()),
            [
                'sum/doc/sumzad.pdf',
                'sum/in/sum0.in',
                'sum/in/sum1a.in',
                'sum/in/sum1b.in',
                'sum/in/sum1ocen.in',
                'sum/in/sum2.in',
                'sum/in/sum3.in',
                'sum/out/sum0.out',
                'sum/out/sum1a.out',
                'sum/out/sum1b.out',
                'sum/out/sum1ocen.out',
                'sum/out/sum2.out',
                'sum/out/sum3.out',
                'sum/prog/sum.c',
                'sum/prog/sumb0.c',
                'sum/prog/sums1.cpp',
            ],
        )


class TestJudging(TestCase):
    fixtures = [
        'test_users',
        'test_contest',
        'test_full_package',
        'test_problem_instance',
    ]

    def test_judging(self):
        self.assertTrue(self.client.login(username='test_user'))
        contest = Contest.objects.get()
        url = reverse('submit', kwargs={'contest_id': contest.id})

        # Show submission form
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertIn(
            'contests/submit.html',
            [getattr(t, 'name', None) for t in response.templates],
        )
        form = response.context['form']
        self.assertEqual(len(form.fields['problem_instance_id'].choices), 1)
        pi_id = form.fields['problem_instance_id'].choices[0][0]

        # Submit
        filename = get_test_filename('sum-various-results.cpp')
        response = self.client.post(
            url, {'problem_instance_id': pi_id, 'file': open(filename, 'rb')}
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Submission.objects.count(), 1)
        self.assertEqual(TestReport.objects.count(), 6)
        self.assertEqual(TestReport.objects.filter(status='OK').count(), 4)
        self.assertEqual(TestReport.objects.filter(status='WA').count(), 1)
        self.assertEqual(TestReport.objects.filter(status='RE').count(), 1)
        submission = Submission.objects.get()
        self.assertEqual(submission.status, 'INI_OK')
        self.assertEqual(submission.score, IntegerScore(34))

        urc = UserResultForContest.objects.get()
        self.assertEqual(urc.score, IntegerScore(34))


@needs_linux
class TestLimits(TestCase):
    fixtures = ['test_users', 'test_contest']

    def upload_package(self):
        ProblemInstance.objects.all().delete()
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
        return self.client.post(
            url,
            {
                'package_file': open(filename, 'rb'),
                'visibility': Problem.VISIBILITY_PRIVATE,
            },
            follow=True,
        )

    @override_settings(MAX_TEST_TIME_LIMIT_PER_PROBLEM=2000)
    def test_time_limit(self):
        response = self.upload_package()
        self.assertContains(
            response,
            escape(
                "Sum of time limits for all tests is too big. It's "
                "50s, but it shouldn't exceed 2s."
            ),
        )

    @override_settings(MAX_MEMORY_LIMIT_FOR_TEST=10)
    def test_memory_limit(self):
        response = self.upload_package()
        self.assertContains(
            response,
            escape(
                "Memory limit mustn't be greater than %dKiB"
                % settings.MAX_MEMORY_LIMIT_FOR_TEST
            ),
        )
