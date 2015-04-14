from django.utils.translation import ugettext_lazy as _
from oioioi.oi.controllers import OIContestController
from oioioi.contests.controllers import PublicContestRegistrationController
from oioioi.participants.controllers import ParticipantsController


class OntakContestController(OIContestController):
    description = _("ONTAK")
    create_forum = False

    def registration_controller(self):
        return ParticipantsController(self.contest)

    def can_see_ranking(self, request):
        return True

    def should_confirm_submission_receipt(self, request, submission):
        return False


class OntakEternalController(OntakContestController):
    description = _("ONTAK-eternal")
    create_forum = False

    def registration_controller(self):
        return PublicContestRegistrationController(self.contest)
