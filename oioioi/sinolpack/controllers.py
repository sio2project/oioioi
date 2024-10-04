from django.utils.translation import gettext_lazy as _

from oioioi.interactive.controllers import InteractiveProblemController
from oioioi.programs.controllers import ProgrammingProblemController
from oioioi.sinolpack.admin import SinolpackProblemAdminMixin
from oioioi.sinolpack.utils import add_extra_files


class SinolProblemController(ProgrammingProblemController):
    description = _("Sinol package problem")

    def fill_evaluation_environ(self, environ, submission, **kwargs):
        super(SinolProblemController, self).fill_evaluation_environ(
            environ, submission, **kwargs
        )
        add_extra_files(environ, self.problem)

    def mixins_for_admin(self):
        return super(SinolProblemController, self).mixins_for_admin() + (
            SinolpackProblemAdminMixin,
        )


class SinolInteractiveProblemController(InteractiveProblemController):
    description = _("Sinol package interactive problem")

    def fill_evaluation_environ(self, environ, submission, **kwargs):
        super(SinolInteractiveProblemController, self).fill_evaluation_environ(
            environ, submission, **kwargs
        )
        add_extra_files(environ, self.problem)

    def mixins_for_admin(self):
        return super(SinolInteractiveProblemController, self).mixins_for_admin() + (
            SinolpackProblemAdminMixin,
        )
