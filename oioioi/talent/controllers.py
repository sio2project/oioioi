from django.conf import settings
from oioioi.participants.controllers import OpenParticipantsController
from oioioi.participants.utils import is_participant
from oioioi.programs.controllers import ProgrammingContestController
from django.utils.translation import gettext_lazy as _
from oioioi.contests.utils import is_contest_admin
from oioioi.talent.forms import TalentRegistrationForm

class TalentRegistrationController(OpenParticipantsController):
    @property
    def form_class(self):
        return TalentRegistrationForm
    
    @classmethod
    def allow_login_as_public_name(self):
        """Determines if participants may choose to stay anonymous,
        i.e. use their logins as public names.
        """
        return False

    def can_register(self, request):
        return bool(not settings.TALENT_REGISTRATION_CLOSED)
    def can_edit_registration(self, request, participant):
        if self.form_class is None:
            return False
        if is_contest_admin(request):
            return True
        if participant.status == 'BANNED':
            return False
        return bool(request.user == participant.user and 
                    not settings.TALENT_REGISTRATION_CLOSED)

class TalentTrialContestController(ProgrammingContestController):
    description = _("Talent camp trial contest")

    def fill_evaluation_environ(self, environ, submission):
        super(TalentTrialContestController, self) \
            .fill_evaluation_environ(environ, submission)

        environ['group_scorer'] = 'oioioi.programs.utils.min_group_scorer'
        environ['test_scorer'] = \
            'oioioi.programs.utils.threshold_linear_test_scorer'
    
    def can_submit(self, request, problem_instance, check_round_times=True):
        if is_contest_admin(request):
            return True
        if not is_participant(request):
            return False
        return super(TalentTrialContestController, self).can_submit(request, problem_instance, check_round_times)
    
    def can_see_test_comments(self, request, submissionreport):
        return is_contest_admin(request)
    
    def registration_controller(self):
        return TalentRegistrationController(self.contest)
