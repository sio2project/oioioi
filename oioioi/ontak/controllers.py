from django.utils.translation import gettext_lazy as _

from oioioi.contests.controllers import PublicContestRegistrationController
from oioioi.oi.controllers import OIContestController
from oioioi.participants.controllers import ParticipantsController


class OntakContestController(OIContestController):
    description = _("ONTAK")
    create_forum = False

    def registration_controller(self):
        return ParticipantsController(self.contest)

    def should_confirm_submission_receipt(self, request, submission):
        return False


class OntakEternalController(OntakContestController):
    description = _("ONTAK-eternal")
    create_forum = False

    def registration_controller(self):
        return PublicContestRegistrationController(self.contest)
