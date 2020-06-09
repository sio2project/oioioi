from django.conf import settings
from django.utils.translation import ugettext_lazy as _
from django.db.models import Q

from oioioi.contests.utils import is_contest_admin
from oioioi.contests.models import Submission
from oioioi.contests.controllers import RegistrationController
from oioioi.programs.controllers import ProgrammingContestController
from oioioi.programs.utils import filter_model_submissions, is_model_submission


class UserContestRegistrationControler(RegistrationController):
    description = _("User contest")

    def can_enter_contest(self, request):
        return True

    def anonymous_can_enter_contest(self):
        return True;

    def user_contests_query(self, request):
        if request.user.is_anonymous:
            # query that returns an empty set
            return Q(pk__isnull=True)

        # all contests that were visited by the user
        return Q(contestview__user=request.user)

    def filter_participants(self, queryset):
        return queryset

    def filter_users_with_accessible_personal_data(self, queryset):
        submissions = Submission.objects.filter(
                problem_instance__contest=self.contest)
        authors = [s.user for s in submissions]
        return [q for q in queryset if q in authors]


class UserContestController(ProgrammingContestController):
    description = _("Contest for everyone")

    def can_see_test(self, request, test):
        # Further restrict access to possibly copyrighted stuff
        return is_contest_admin(request)

    def can_see_checker_exe(self, request, checker):
        # Further restrict access to possibly copyrighted stuff
        return is_contest_admin(request)

    def can_submit(self, request, problem_instance, check_round_times=True):
        if settings.ARCHIVE_USERCONTESTS:
            return False
        return super(UserContestController, self) \
                .can_submit(request, problem_instance, check_round_times)

    def filter_visible_sources(self, request, queryset):
        # With ARCHIVE_USERCONTESTS=True observers can be regular users who were
        # once basicadmins - so disallow observers from seeing model solutions
        if not is_contest_admin(request):
            queryset = filter_model_submissions(queryset)

        return super(UserContestController, self) \
                .filter_visible_sources(request, queryset)

    def can_see_source(self, request, submission):
        # With ARCHIVE_USERCONTESTS=True observers can be regular users who were
        # once basicadmins - so disallow observers from seeing model solutions
        if not is_contest_admin(request) and is_model_submission(submission):
            return False

        return super(UserContestController, self) \
                .can_see_source(request, submission)

    def registration_controller(self):
        return UserContestRegistrationControler(self.contest)
