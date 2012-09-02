from django.utils.translation import ugettext_lazy as _
from django.template.response import TemplateResponse
from oioioi.contests.controllers import ContestController, \
        RegistrationController

class TeacherRegistraionController(RegistrationController):
    def filter_participants(self, queryset):
        return queryset.filter(participant__contest=self.contest)

    def anonymous_can_enter_contest(self):
        return False

    def no_entry_view(self, request):
        return TemplateResponse(request, 'teachers/no_entry.html')

class TeacherContestController(ContestController):
    description = _("Contest for teachers")

    def registration_controller(self):
        return TeacherRegistraionController(self.contest)
