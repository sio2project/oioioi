from django.utils.translation import gettext_lazy as _

from oioioi.filetracker.utils import django_to_filetracker_path
from oioioi.interactive.models import Interactor, InteractiveTaskInfo
from oioioi.programs.controllers import ProgrammingProblemController


class InteractiveProblemController(ProgrammingProblemController):
    description = _("Interactive programming problem")

    def fill_evaluation_environ(self, environ, submission, **kwargs):
        super().fill_evaluation_environ(environ, submission, **kwargs)

        interactor = Interactor.objects.get(problem=self.problem)
        environ['interactor_file'] = django_to_filetracker_path(interactor.exe_file)
        info = InteractiveTaskInfo.objects.get(problem=self.problem)
        environ['num_processes'] = info.num_processes

        environ['task_type_suffix'] = '-interactive-exec'

    def user_outs_exist(self):
        return False

    def allow_test_runs(self, request):
        return False
