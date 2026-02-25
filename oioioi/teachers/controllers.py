from django.template.response import TemplateResponse
from django.utils.translation import gettext_lazy as _

from oioioi.participants.controllers import ParticipantsController
from oioioi.programs.controllers import ProgrammingContestController
from oioioi.rankings.controllers import DefaultRankingController


class TeacherRegistrationController(ParticipantsController):
    @property
    def form_class(self):
        return None

    @property
    def participant_admin(self):
        return None

    def can_register(self, request):
        return False

    def can_edit_registration(self, request, participant):
        return False

    def no_entry_view(self, request):
        return TemplateResponse(request, "teachers/no_entry.html")


class TeacherRankingController(DefaultRankingController):
    def filter_users_for_ranking(self, key, queryset):
        queryset = super().filter_users_for_ranking(key, queryset)
        return self.contest.controller.registration_controller().filter_participants(queryset)


class TeacherContestController(ProgrammingContestController):
    description = _("Contest for teachers")
    create_forum = True

    def uses_threshold_linear_scoring(self):
        return True

    def fill_evaluation_environ(self, environ, submission):
        environ["group_scorer"] = "oioioi.programs.utils.min_group_scorer"
        environ["test_scorer"] = "oioioi.programs.utils.threshold_linear_test_scorer"

        super().fill_evaluation_environ(environ, submission)

    def registration_controller(self):
        return TeacherRegistrationController(self.contest)

    def ranking_controller(self):
        return TeacherRankingController(self.contest)
