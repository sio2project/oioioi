from django.utils.translation import ugettext_lazy as _

from oioioi.problems.controllers import ProblemController
from oioioi.zeus.admin import ZeusProblemAdminMixin


class ZeusProblemController(ProblemController):
    description = _("Zeus problem")

    def mixins_for_admin(self):
        return super(ZeusProblemController, self).mixins_for_admin() + \
                (ZeusProblemAdminMixin,)
