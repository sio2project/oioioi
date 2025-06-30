import logging

from django.conf import settings
from django.db.models import Q
from django.shortcuts import redirect
from django.template.loader import render_to_string
from django.template.response import TemplateResponse
from django.utils.translation import gettext_lazy as _

from oioioi.base.utils.query_helpers import Q_always_true
from oioioi.base.utils.redirect import safe_redirect
from oioioi.contests.controllers import (
    PastRoundsHiddenContestControllerMixin,
    PublicContestRegistrationController,
)
from oioioi.contests.models import Submission, SubmissionReport
from oioioi.contests.utils import (
    can_see_personal_data,
    is_contest_admin,
    is_contest_observer,
)
from oioioi.oi.models import OIRegistration
from oioioi.participants.controllers import (
    OnsiteContestControllerMixin,
    ParticipantsController,
)
from oioioi.participants.models import Participant
from oioioi.participants.utils import is_participant
from oioioi.programs.controllers import ProgrammingContestController
from oioioi.scoresreveal.utils import is_revealed
from oioioi.contests.models import RegistrationStatus

auditLogger = logging.getLogger(__name__ + ".audit")


class OIRegistrationController(ParticipantsController):
    @property
    def form_class(self):
        from oioioi.oi.forms import OIRegistrationForm

        return OIRegistrationForm

    @property
    def participant_admin(self):
        from oioioi.oi.admin import OIRegistrationParticipantAdmin

        return OIRegistrationParticipantAdmin

    @classmethod
    def anonymous_can_enter_contest(cls):
        return True

    # Redundant because of filter_visible_contests, but saves a db query
    def can_enter_contest(self, request):
        return True

    def visible_contests_query(self, request):
        return Q_always_true()

    def can_register(self, request):
        return super().is_registration_open(request)

    def get_registration_status(self, request):
        return super().registration_status(request)

    def can_unregister(self, request, participant):
        return False

    def registration_view(self, request):

        registration_status = self.get_registration_status(request)
        if registration_status == RegistrationStatus.NOT_OPEN_YET:
            return TemplateResponse(request, 'contests/registration_not_open_yet.html')

        participant = self._get_participant_for_form(request)

        if 'oi_oiregistrationformdata' in request.session:
            # pylint: disable=not-callable
            form = self.form_class(request.session['oi_oiregistrationformdata'])
            del request.session['oi_oiregistrationformdata']
        else:
            form = self.get_form(request, participant)
        form.set_terms_accepted_text(self.get_terms_accepted_phrase())

        if request.method == 'POST':
            if '_add_school' in request.POST:
                data = request.POST.copy()
                data.pop('_add_school', None)
                data.pop('csrfmiddlewaretoken', None)
                request.session['oi_oiregistrationformdata'] = data
                return redirect('add_school')
            elif form.is_valid():  # pylint: disable=maybe-no-member
                participant, created = Participant.objects.get_or_create(
                    contest=self.contest, user=request.user
                )

                auditLogger.info(
                    "User %d (%s) registered in %s from IP %s UA: %s",
                    request.user.id,
                    request.user.username,
                    self.contest.id,
                    request.META.get('REMOTE_ADDR', '?'),
                    request.headers.get('user-agent', '?'),
                )
                self.handle_validated_form(request, form, participant)
                if 'next' in request.GET:
                    return safe_redirect(request, request.GET['next'])
                else:
                    return redirect('default_contest_view', contest_id=self.contest.id)

        context = {'form': form, 'participant': participant}
        return TemplateResponse(request, self.registration_template, context)

    def get_contest_participant_info_list(self, request, user):
        prev = super(OIRegistrationController, self).get_contest_participant_info_list(
            request, user
        )

        if can_see_personal_data(request):
            sensitive_info = OIRegistration.objects.filter(
                participant__user=user, participant__contest=request.contest
            )
            if sensitive_info.exists():
                context = {'model': sensitive_info[0]}
                rendered_sensitive_info = render_to_string(
                    'oi/sensitive_participant_info.html',
                    context=context,
                    request=request,
                )
                prev.append((2, rendered_sensitive_info))

        return prev

    def mixins_for_admin(self):
        from oioioi.participants.admin import TermsAcceptedPhraseAdminMixin

        return super(OIRegistrationController, self).mixins_for_admin() + (
            TermsAcceptedPhraseAdminMixin,
        )

    def can_change_terms_accepted_phrase(self, request):
        return not OIRegistration.objects.filter(
            participant__contest=request.contest
        ).exists()


class OIContestController(ProgrammingContestController):
    description = _("Polish Olympiad in Informatics - Online")
    create_forum = True
    show_email_in_participants_data = True
    scoring_description = _(
        "The solutions are judged with sio2jail. They can be scored from 0 to 100 points. "
        "If the submission runs for longer than half of the time limit, the points for this test are linearly decreased to 0.\n"
        "The score for a group of test cases is the minimum score for any of the test cases.\n"
        "The ranking is determined by the total score.\n"
        "Until the end of the contest, participants can only see scoring of their submissions on example test cases. "
        "Full scoring is available after the end of the contest."
        )

    def fill_evaluation_environ(self, environ, submission):
        super(OIContestController, self).fill_evaluation_environ(environ, submission)

        environ['group_scorer'] = 'oioioi.programs.utils.min_group_scorer'
        environ['test_scorer'] = 'oioioi.programs.utils.threshold_linear_test_scorer'

    def registration_controller(self):
        return OIRegistrationController(self.contest)

    def can_submit(self, request, problem_instance, check_round_times=True):
        if request.user.is_anonymous:
            return False
        if request.user.has_perm('contests.contest_admin', self.contest):
            return True
        if not is_participant(request):
            return False
        return super(OIContestController, self).can_submit(
            request, problem_instance, check_round_times
        )

    def can_see_stats(self, request):
        return is_contest_admin(request) or is_contest_observer(request)

    def should_confirm_submission_receipt(self, request, submission):
        return submission.kind == 'NORMAL' and request.user == submission.user

    def update_user_result_for_problem(self, result):
        try:
            latest_submission = (
                Submission.objects.filter(problem_instance=result.problem_instance)
                .filter(user=result.user)
                .filter(score__isnull=False)
                .exclude(status='CE')
                .filter(kind='NORMAL')
                .latest()
            )
            try:
                report = SubmissionReport.objects.get(
                    submission=latest_submission, status='ACTIVE', kind='NORMAL'
                )
            except SubmissionReport.DoesNotExist:
                report = None
            result.score = latest_submission.score
            result.status = latest_submission.status
            result.submission_report = report
        except Submission.DoesNotExist:
            result.score = None
            result.status = None
            result.submission_report = None

    def default_can_see_ranking(self, request):
        return is_contest_admin(request) or is_contest_observer(request)

    def default_contestlogo_url(self):
        return '%(url)soi/logo.png' % {'url': settings.STATIC_URL}

    def default_contesticons_urls(self):
        return [
            '%(url)simages/menu/menu-icon-%(i)d.png'
            % {'url': settings.STATIC_URL, 'i': i}
            for i in range(1, 4)
        ]


class OIOnsiteContestController(OIContestController):
    description = _("Polish Olympiad in Informatics - Onsite")
    scoring_description = _(
        "The solutions are judged with sio2jail. They can be scored from 0 to 100 points. "
        "If the submission runs for longer than half of the time limit, the points for this test are linearly decreased to 0.\n"
        "The score for a group of test cases is the minimum score for any of the test cases.\n"
        "The ranking is determined by the total score.\n"
        "Until the end of the contest, participants can only see scoring of their submissions on example test cases. "
        "Full scoring is available after the end of the contest."
        )


OIOnsiteContestController.mix_in(OnsiteContestControllerMixin)
OIOnsiteContestController.mix_in(PastRoundsHiddenContestControllerMixin)


class OIFinalOnsiteContestController(OIOnsiteContestController):
    description = _("Polish Olympiad in Informatics - Onsite - Finals")
    scoring_description = _(
        "The solutions are judged with sio2jail. They can be scored from 0 to 100 points. "
        "If the submission runs for longer than half of the time limit, the points for this test are linearly decreased to 0.\n"
        "The score for a group of test cases is the minimum score for any of the test cases\n."
        "The ranking is determined by the total score.\n"
        "Full scoring of the submissions can be revealed during the contest."
        )

    def can_see_submission_score(self, request, submission):
        return True

    def update_user_result_for_problem(self, result):
        submissions = (
            Submission.objects.filter(problem_instance=result.problem_instance)
            .filter(user=result.user)
            .filter(score__isnull=False)
            .exclude(status='CE')
            .filter(kind='NORMAL')
        )

        if submissions:
            max_submission = submissions.order_by('-score')[0]

            try:
                report = SubmissionReport.objects.get(
                    submission=max_submission, status='ACTIVE', kind='NORMAL'
                )
            except SubmissionReport.DoesNotExist:
                report = None

            result.score = max_submission.score
            result.status = max_submission.status
            result.submission_report = report
        else:
            result.score = None
            result.status = None
            result.submission_report = None


class BOIOnsiteContestController(OIOnsiteContestController):
    description = _("Baltic Olympiad in Informatics")
    create_forum = False

    def can_see_test_comments(self, request, submissionreport):
        submission = submissionreport.submission
        return is_contest_admin(request) or self.results_visible(request, submission)

    def reveal_score(self, request, submission):
        super(BOIOnsiteContestController, self).reveal_score(request, submission)
        self.update_user_results(submission.user, submission.problem_instance)

    def update_user_result_for_problem(self, result):
        try:
            submissions = (
                Submission.objects.filter(problem_instance=result.problem_instance)
                .filter(user=result.user)
                .filter(score__isnull=False)
                .exclude(status='CE')
                .filter(kind='NORMAL')
            )

            chosen_submission = submissions.latest()

            revealed = submissions.filter(revealed__isnull=False)
            if revealed:
                max_revealed = revealed.order_by('-score')[0]
                if max_revealed.score > chosen_submission.score:
                    chosen_submission = max_revealed

            try:
                report = SubmissionReport.objects.get(
                    submission=chosen_submission, status='ACTIVE', kind='NORMAL'
                )
            except SubmissionReport.DoesNotExist:
                report = None

            result.score = chosen_submission.score
            result.status = chosen_submission.status
            result.submission_report = report
        except Submission.DoesNotExist:
            result.score = None
            result.status = None
            result.submission_report = None

    def get_visible_reports_kinds(self, request, submission):
        if is_revealed(submission) or self.results_visible(request, submission):
            return ['USER_OUTS', 'INITIAL', 'NORMAL']
        else:
            return ['USER_OUTS', 'INITIAL']

    def can_print_files(self, request):
        return True

    def default_contestlogo_url(self):
        return None

    def default_contesticons_urls(self):
        return []

    def fill_evaluation_environ(self, environ, submission):
        super(BOIOnsiteContestController, self).fill_evaluation_environ(
            environ, submission
        )

        environ['test_scorer'] = 'oioioi.programs.utils.discrete_test_scorer'


class BOIOnlineContestController(BOIOnsiteContestController):
    description = _("Baltic Olympiad in Informatics - online")
    create_forum = False

    def registration_controller(self):
        return PublicContestRegistrationController(self.contest)

    def is_onsite(self):
        return False
