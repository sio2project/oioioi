# coding: utf-8

from django.test import TestCase
from django.core.management import call_command
from oioioi.problems.package import backend_for_package
from oioioi.sinolpack.package import SinolPackageBackend, \
        DEFAULT_TIME_LIMIT, DEFAULT_MEMORY_LIMIT
from oioioi.problems.models import Problem, ProblemStatement, \
        ProblemAttachment
from oioioi.programs.models import Test, OutputChecker, ModelSolution
from oioioi.sinolpack.models import ExtraConfig, ExtraFile
from nose.plugins.attrib import attr
import os.path

class TestSinolPackage(TestCase):
    def _package_filename(self, name):
        return os.path.join(os.path.dirname(__file__), 'files', name)

    def test_identify_zip(self):
        filename = self._package_filename('test_simple_package.zip')
        self.assert_(SinolPackageBackend().identify(filename))

    def test_identify_tgz(self):
        filename = self._package_filename('test_full_package.tgz')
        self.assert_(SinolPackageBackend().identify(filename))

    def _check_full_package(self, problem, doc=True):
        self.assertEqual(problem.short_name, 'sum')

        config = ExtraConfig.objects.get(problem=problem)
        assert 'extra_compilation_args' in config.parsed_config

        if doc:
            self.assertEqual(problem.name, u'Sumżyce')
            statements = ProblemStatement.objects.filter(problem=problem)
            self.assertEqual(statements.count(), 1)
            self.assert_(statements.get().content.read().startswith('%PDF'))
        else:
            self.assertEqual(problem.name, u'sum')

        tests = Test.objects.filter(problem=problem)
        t0 = tests.get(name='0')
        self.assertEqual(t0.input_file.read(), '1 2\n')
        self.assertEqual(t0.output_file.read(), '3\n')
        self.assertEqual(t0.kind, 'EXAMPLE')
        self.assertIsNone(t0.group)
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
        self.assertIsNone(t1ocen.group)
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
        self.assertIsNotNone(checker.exe_file)

        extra_files = ExtraFile.objects.filter(problem=problem)
        self.assertEqual(extra_files.count(), 1)
        self.assertEqual(extra_files.get().name, 'makra.h')

        model_solutions = ModelSolution.objects.filter(problem=problem)
        sol = model_solutions.get(name='sum.c')
        self.assertEqual(sol.kind, 'NORMAL')
        sol1 = model_solutions.get(name='sum1.pas')
        self.assertEqual(sol1.kind, 'NORMAL')
        sols1 = model_solutions.get(name='sums1.cpp')
        self.assertEqual(sols1.kind, 'SLOW')
        solb0 = model_solutions.get(name='sumb0.c')
        self.assertEqual(solb0.kind, 'INCORRECT')
        self.assertEqual(model_solutions.count(), 4)

        tests = Test.objects.filter(problem=problem)

    @attr('slow')
    def test_full_unpack_and_update(self):
        filename = self._package_filename('test_full_package.tgz')
        call_command('addproblem', filename)
        problem = Problem.objects.get()
        self._check_full_package(problem)

        # Rudimentary test of package updating
        call_command('updateproblem', str(problem.id), filename)
        problem = Problem.objects.get()
        self._check_full_package(problem)
