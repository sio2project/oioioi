from django.utils.translation import ugettext_lazy as _
from django.template.response import TemplateResponse
from oioioi.contests.controllers import RegistrationController
from oioioi.programs.controllers import ProgrammingContestController
from oioioi.rankings.controllers import DefaultRankingController

class TeacherRegistraionController(RegistrationController):
    def filter_participants(self, queryset):
        return queryset.filter(pupil__contest=self.contest)

    def anonymous_can_enter_contest(self):
        return False

    def no_entry_view(self, request):
        return TemplateResponse(request, 'teachers/no_entry.html')

class TeacherRankingController(DefaultRankingController):
    def filter_users_for_ranking(self, request, key, queryset):
        return queryset.filter(pupil__contest=self.contest)

class TeacherContestController(ProgrammingContestController):
    description = _("Contest for teachers")

    def registration_controller(self):
        return TeacherRegistraionController(self.contest)

    def ranking_controller(self):
        return TeacherRankingController(self.contest)
