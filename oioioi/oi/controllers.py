from django.utils.translation import ugettext_lazy as _
from django.contrib.auth.models import User
from oioioi.contests.models import Submission
from oioioi.contests.utils import has_any_active_round
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

    def can_register(self, request):
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

    def update_user_result_for_problem(self, result):
        try:
            latest_submission = Submission.objects \
                .filter(problem_instance=result.problem_instance) \
                .filter(user=result.user) \
                .filter(score__isnull=False) \
                .exclude(status='CE') \
                .filter(kind='NORMAL') \
                .latest()
            result.score = latest_submission.score
            result.status = latest_submission.status
        except Submission.DoesNotExist:
            result.score = None
            result.status = None
        result.save()

class OIOnsiteRegistrationController(ParticipantsController):
    participant_admin = OIOnsiteRegistrationParticipantAdmin

    def can_register(self, request):
        return False

    def can_edit_registration(self, request, participant):
        return False

class OIOnsiteContestController(OIContestController):
    description = _("Polish Olympiad in Informatics - Onsite")

    def registration_controller(self):
        return OIOnsiteRegistrationController(self.contest)

    def can_see_round(self, request, round):
        if request.user.has_perm('contests.contest_admin', request.contest):
            return True
        rtimes = self.get_round_times(request, round)
        if has_any_active_round(request):
            return rtimes.is_active(request.timestamp)
        return super(OIOnsiteContestController, self) \
                .can_see_round(request, round)
