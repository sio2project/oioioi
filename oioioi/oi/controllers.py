from django.utils.translation import ugettext_lazy as _

from oioioi.contests.models import Submission, SubmissionReport
from oioioi.contests.utils import has_any_active_round
from oioioi.programs.controllers import ProgrammingContestController
from oioioi.participants.controllers import ParticipantsController
from oioioi.participants.utils import is_participant
from oioioi.spliteval.controllers import SplitEvalContestControllerMixin

class OIRegistrationController(ParticipantsController):
    @property
    def form_class(self):
        from oioioi.oi.forms import OIRegistrationForm
        return OIRegistrationForm

    @property
    def participant_admin(self):
        from oioioi.oi.admin import OIRegistrationParticipantAdmin
        return OIRegistrationParticipantAdmin

    def anonymous_can_enter_contest(self):
        return True

    def can_enter_contest(self, request):
        return True

    def can_register(self, request):
        return True

class OIContestController(ProgrammingContestController):
    description = _("Polish Olympiad in Informatics - Online")

    def fill_evaluation_environ(self, environ, submission):
        environ['group_scorer'] = 'oioioi.programs.utils.min_group_scorer'
        environ['test_scorer'] = \
                'oioioi.programs.utils.threshold_linear_test_scorer'

        super(OIContestController, self) \
                .fill_evaluation_environ(environ, submission)

    def registration_controller(self):
        return OIRegistrationController(self.contest)

    def can_submit(self, request, problem_instance):
        if request.user.is_anonymous():
            return False
        if request.user.has_perm('contests.contest_admin', self.contest):
            return True
        if not is_participant(request):
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
            try:
                report = SubmissionReport.objects.get(
                        submission=latest_submission, status='ACTIVE',
                        kind='NORMAL')
            except SubmissionReport.DoesNotExist:
                report = None
            result.score = latest_submission.score
            result.status = latest_submission.status
            result.submission_report = report
        except Submission.DoesNotExist:
            result.score = None
            result.status = None
            result.submission_report = None
        result.save()
OIContestController.mix_in(SplitEvalContestControllerMixin)


class OIOnsiteRegistrationController(ParticipantsController):
    @property
    def participant_admin(self):
        from oioioi.oi.admin import OIOnsiteRegistrationParticipantAdmin
        return OIOnsiteRegistrationParticipantAdmin

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
