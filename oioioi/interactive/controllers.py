from oioioi.interactive.models import Interactor
from oioioi.programs.controllers import ProgrammingProblemController


class InteractiveProblemController(ProgrammingProblemController):

    def fill_evaluation_environ(self, environ, submission, **kwargs):
        super().fill_evaluation_environ(environ, submission, **kwargs)

        interactor = Interactor.objects.get(problem=self.problem)
        environ['interactor_file'] = interactor.exe_file

        environ['task_type_suffix'] = '-interactive-exec'
