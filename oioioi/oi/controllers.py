# pylint: disable=E1103
# Instance of 'OIRegistrationForm' has no 'is_valid' member
from django.shortcuts import redirect
from django.template.response import TemplateResponse
from django.utils.translation import ugettext_lazy as _
from django.conf import settings

from oioioi.base.utils.redirect import safe_redirect
from oioioi.contests.controllers import PastRoundsHiddenContestControllerMixin
from oioioi.contests.models import Submission, SubmissionReport
from oioioi.contests.utils import is_contest_admin, is_contest_observer
from oioioi.programs.controllers import ProgrammingContestController
from oioioi.participants.controllers import ParticipantsController
from oioioi.participants.models import Participant
from oioioi.participants.utils import is_participant
from oioioi.oi.models import OIOnsiteRegistration
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

    def can_unregister(self, request, participant):
        return False

    def registration_view(self, request):
        participant = self._get_participant_for_form(request)

        if 'oi_oiregistrationformdata' in request.session:
            form = self.form_class(request.session[
                                   'oi_oiregistrationformdata'])
            del request.session['oi_oiregistrationformdata']
        else:
            form = self.get_form(request, participant)
        if request.method == 'POST':
            if '_add_school' in request.POST:
                data = request.POST.copy()
                data.pop('_add_school', None)
                data.pop('csrfmiddlewaretoken', None)
                request.session['oi_oiregistrationformdata'] = data
                return redirect('add_school')
            elif form.is_valid():
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


class OIContestController(ProgrammingContestController):
    description = _("Polish Olympiad in Informatics - Online")
    create_forum = True

    def fill_evaluation_environ(self, environ, submission):
        environ['group_scorer'] = 'oioioi.programs.utils.min_group_scorer'
        environ['test_scorer'] = \
                'oioioi.programs.utils.threshold_linear_test_scorer'

        super(OIContestController, self) \
                .fill_evaluation_environ(environ, submission)

    def registration_controller(self):
        return OIRegistrationController(self.contest)

    def can_submit(self, request, problem_instance, check_round_times=True):
        if request.user.is_anonymous():
            return False
        if request.user.has_perm('contests.contest_admin', self.contest):
            return True
        if not is_participant(request):
            return False
        return super(OIContestController, self)\
                .can_submit(request, problem_instance, check_round_times)

    def can_see_stats(self, request):
        return is_contest_admin(request) or is_contest_observer(request)

    def should_confirm_submission_receipt(self, request, submission):
        return submission.kind == 'NORMAL' and request.user == submission.user

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

    def can_see_ranking(self, request):
        return is_contest_admin(request) or is_contest_observer(request)

    def default_contestlogo_url(self):
        return '%(url)soi/logo.png' % {'url': settings.STATIC_URL}

    def default_contesticons_urls(self):
        return ['%(url)simages/menu/menu-icon-%(i)d.png' %
                {'url': settings.STATIC_URL, 'i': i} for i in range(1, 4)]
OIContestController.mix_in(SplitEvalContestControllerMixin)


class OIOnsiteRegistrationController(ParticipantsController):
    @property
    def participant_admin(self):
        from oioioi.oi.admin import OIOnsiteRegistrationParticipantAdmin
        return OIOnsiteRegistrationParticipantAdmin

    def get_model_class(self):
        return OIOnsiteRegistration

    def can_register(self, request):
        return False

    def can_edit_registration(self, request, participant):
        return False


class OIOnsiteContestController(OIContestController):
    description = _("Polish Olympiad in Informatics - Onsite")
    create_forum = False

    def registration_controller(self):
        return OIOnsiteRegistrationController(self.contest)

    def should_confirm_submission_receipt(self, request, submission):
        return False
OIOnsiteContestController.mix_in(PastRoundsHiddenContestControllerMixin)
