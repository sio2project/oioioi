from django.utils.translation import gettext_lazy as _

from oioioi.encdec.controllers import EncdecProblemController
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


class SinolEncdecProblemController(EncdecProblemController):
    description = _("Sinol package encoder-decoder problem")

    def fill_evaluation_environ(self, environ, submission, **kwargs):
        super(SinolEncdecProblemController, self).fill_evaluation_environ(
            environ, submission, **kwargs
        )
        add_extra_files(environ, self.problem)

    def mixins_for_admin(self):
        return super(SinolEncdecProblemController, self).mixins_for_admin() + (
            SinolpackProblemAdminMixin,
        )
