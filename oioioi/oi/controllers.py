from django.utils.translation import ugettext_lazy as _
from oioioi.programs.controllers import ProgrammingContestController
from oioioi.participants.controllers import ParticipantsController
from oioioi.oi.models import OIRegistration, School
from oioioi.oi.admin import OIRegistrationParticipantAdmin, \
                        OIOnsiteRegistrationParticipantAdmin
from oioioi.oi.forms import OIRegistrationForm

class OIRegistrationController(ParticipantsController):
    form_class = OIRegistrationForm
    participant_admin = OIRegistrationParticipantAdmin

    def anonymous_can_enter_contest(self):
        return True

    def can_enter_contest(self, request):
        return True

class OIContestController(ProgrammingContestController):
    description = _("Polish Olympiad in Informatics - Online")

    def registration_controller(self):
        return OIRegistrationController(self.contest)

    def can_submit(self, request, problem_instance):
        if request.user.is_anonymous():
            return False
        if request.user.has_perm('contests.contest_admin', self.contest):
            return True
        qs = User.objects.filter(id=request.user.id)
        if not self.registration_controller().filter_participants(qs):
            return False
        return super(OIContestController, self)\
                .can_submit(request, problem_instance)

class OIOnsiteRegistrationController(ParticipantsController):
    participant_admin = OIOnsiteRegistrationParticipantAdmin

    def can_register(self, request):
        return False

    def can_edit_registration(self, request):
        return False

class OIOnsiteContestController(ProgrammingContestController):
    description = _("Polish Olympiad in Informatics - Onsite")

    def registration_controller(self):
        return OIOnsiteRegistrationController(self.contest)
