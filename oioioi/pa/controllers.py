# pylint: disable=E1103
# Instance of 'PARegistrationForm' has no 'is_valid' member
from django.shortcuts import redirect
from django.template.response import TemplateResponse
from django.utils.translation import ugettext_lazy as _

from oioioi.base.utils.redirect import safe_redirect
from oioioi.programs.controllers import ProgrammingContestController
from oioioi.participants.controllers import ParticipantsController
from oioioi.participants.models import Participant
from oioioi.participants.utils import is_participant
from oioioi.spliteval.controllers import SplitEvalContestControllerMixin


class PARegistrationController(ParticipantsController):
    @property
    def form_class(self):
        from oioioi.pa.forms import PARegistrationForm
        return PARegistrationForm

    @property
    def participant_admin(self):
        from oioioi.pa.admin import PARegistrationParticipantAdmin
        return PARegistrationParticipantAdmin

    def anonymous_can_enter_contest(self):
        return True

    def can_enter_contest(self, request):
        return True

    def can_register(self, request):
        return True

    def can_unregister(self, request, participant):
        return False

    def registration_view(self, request):
        participant = self._get_participant_for_form(request)

        if 'pa_paregistrationformdata' in request.session:
            form = self.form_class(request.session[
                                   'pa_paregistrationformdata'])
            del request.session['pa_paregistrationformdata']
        else:
            form = self.get_form(request, participant)
        if request.method == 'POST':
            if form.is_valid():
                participant, created = Participant.objects \
                        .get_or_create(contest=self.contest, user=request.user)
                self.handle_validated_form(request, form, participant)
                if 'next' in request.GET:
                    return safe_redirect(request, request.GET['next'])
                else:
                    return redirect('default_contest_view',
                            contest_id=self.contest.id)

        context = {'form': form, 'participant': participant}
        return TemplateResponse(request, self.registration_template, context)


class PAContestController(ProgrammingContestController):
    description = _("Algorithmic Engagements")
    create_forum = True

    def fill_evaluation_environ(self, environ, submission):
        environ['group_scorer'] = 'oioioi.programs.utils.min_group_scorer'
        environ['test_scorer'] = \
                'oioioi.programs.utils.threshold_linear_test_scorer'

        super(PAContestController, self) \
                .fill_evaluation_environ(environ, submission)

    def registration_controller(self):
        return PARegistrationController(self.contest)

    def can_submit(self, request, problem_instance, check_round_times=True):
        if request.user.is_anonymous():
            return False
        if request.user.has_perm('contests.contest_admin', self.contest):
            return True
        if not is_participant(request):
            return False
        return super(PAContestController, self) \
                .can_submit(request, problem_instance, check_round_times)

    def should_confirm_submission_receipt(self, request, submission):
        return submission.kind == 'NORMAL' and request.user == submission.user

PAContestController.mix_in(SplitEvalContestControllerMixin)
