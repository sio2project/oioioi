from django.utils.translation import ugettext_lazy as _
from oioioi.contests.utils import is_contest_admin
from oioioi.oi.controllers import OIContestController
from oioioi.contests.controllers import PublicContestRegistrationController
from oioioi.participants.controllers import ParticipantsController

class OntakContestController(OIContestController):
    description = _("ONTAK")
    create_forum = False

    def registration_controller(self):
        return ParticipantsController(self.contest)

class OntakEternalController(OIContestController):
    description = _("ONTAK-eternal")
    create_forum = False

    def registration_controller(self):
        return PublicContestRegistrationController(self.contest)
