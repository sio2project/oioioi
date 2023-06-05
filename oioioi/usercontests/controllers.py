from django.conf import settings
from django.utils.translation import gettext_lazy as _

from oioioi.contests.utils import is_contest_admin
from oioioi.programs.controllers import ProgrammingContestController
from oioioi.programs.utils import filter_model_submissions, is_model_submission
from oioioi.teachers.controllers import TeacherRegistrationController


class UserContestController(ProgrammingContestController):
    description = _("Contest for everyone")

    def registration_controller(self):
        if settings.HIDE_USERCONTESTS:
            return TeacherRegistrationController(self.contest)
        else:
            return super().registration_controller()

    def can_see_test(self, request, test):
        # Further restrict access to possibly copyrighted stuff
        return is_contest_admin(request)

    def can_see_checker_exe(self, request, checker):
        # Further restrict access to possibly copyrighted stuff
        return is_contest_admin(request)

    def can_submit(self, request, problem_instance, check_round_times=True):
        if settings.ARCHIVE_USERCONTESTS:
            return False
        return super(UserContestController, self).can_submit(
            request, problem_instance, check_round_times
        )

    def filter_visible_sources(self, request, queryset):
        # With ARCHIVE_USERCONTESTS=True observers can be regular users who were
        # once basicadmins - so disallow observers from seeing model solutions
        if not is_contest_admin(request):
            queryset = filter_model_submissions(queryset)

        return super(UserContestController, self).filter_visible_sources(
            request, queryset
        )

    def can_see_source(self, request, submission):
        # With ARCHIVE_USERCONTESTS=True observers can be regular users who were
        # once basicadmins - so disallow observers from seeing model solutions
        if not is_contest_admin(request) and is_model_submission(submission):
            return False

        return super(UserContestController, self).can_see_source(request, submission)
