from django.utils.translation import ugettext_lazy as _

from oioioi.programs.controllers import ProgrammingContestController


class UserContestController(ProgrammingContestController):
    description = _("Contest for everyone")

    def can_see_test(self, request, test):
        # Further restrict access to possibly copyrighted stuff
        return is_contest_admin(request)

    def can_see_checker_exe(self, request, checker):
        # Further restrict access to possibly copyrighted stuff
        return is_contest_admin(request)
