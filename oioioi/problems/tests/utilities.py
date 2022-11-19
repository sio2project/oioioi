import os.path

from django import forms

from oioioi.problems.controllers import ProblemController
from oioioi.problems.models import Problem, ProblemPackage
from oioioi.problems.package import ProblemPackageBackend
from oioioi.problems.problem_sources import UploadedPackageSource
from oioioi.programs.controllers import ProgrammingContestController


class AssertContainsOnlyMixin:
    def assert_contains_only(self, response, allowed_values):
        for task in self.all_values:
            if task in allowed_values:
                self.assertContains(response, task)
            else:
                self.assertNotContains(response, task)


class TestProblemController(ProblemController):
    __test__ = False

    def fill_evaluation_environ(self, environ, submission, **kwargs):
        raise NotImplementedError


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
            contest=pp.contest,
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


def get_test_filename(name):
    return os.path.join(os.path.dirname(__file__), '../../sinolpack/files', name)
