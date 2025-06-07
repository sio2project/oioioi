from django.shortcuts import redirect
from django.template.loader import render_to_string
from django.template.response import TemplateResponse
from django.utils.translation import gettext_lazy as _

from oioioi.base.utils.query_helpers import Q_always_true
from oioioi.base.utils.redirect import safe_redirect
from oioioi.contests.models import Submission, SubmissionReport
from oioioi.mp.models import MPRegistration, SubmissionScoreMultiplier
from oioioi.mp.score import FloatScore
from oioioi.participants.controllers import ParticipantsController
from oioioi.participants.models import Participant
from oioioi.participants.utils import is_participant
from oioioi.programs.controllers import ProgrammingContestController
from oioioi.rankings.controllers import DefaultRankingController
from oioioi.contests.models import RegistrationStatus

CONTEST_RANKING_KEY = 'c'


class MPRegistrationController(ParticipantsController):
    registration_template = 'mp/registration.html'

    @property
    def form_class(self):
        from oioioi.mp.forms import MPRegistrationForm

        return MPRegistrationForm

    @property
    def participant_admin(self):
        from oioioi.mp.admin import MPRegistrationParticipantAdmin

        return MPRegistrationParticipantAdmin

    @classmethod
    def anonymous_can_enter_contest(self):
        return True

    def allow_login_as_public_name(self):
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

    def registration_view(self, request):

        registration_status = self.get_registration_status(request)
        if registration_status == RegistrationStatus.NOT_OPEN_YET:
            return TemplateResponse(request, 'contests/registration_not_open_yet.html')

        participant = self._get_participant_for_form(request)

        if 'mp_mpregistrationformdata' in request.session:
            # pylint: disable=not-callable
            form = self.form_class(request.session['mp_mpregistrationformdata'])
            del request.session['mp_mpregistrationformdata']
        else:
            form = self.get_form(request, participant)
        form.set_terms_accepted_text(self.get_terms_accepted_phrase())

        if request.method == 'POST':
            # pylint: disable=maybe-no-member
            if form.is_valid():
                participant, created = Participant.objects.get_or_create(
                    contest=self.contest, user=request.user
                )
                self.handle_validated_form(request, form, participant)
                if 'next' in request.GET:
                    return safe_redirect(request, request.GET['next'])
                else:
                    return redirect('default_contest_view', contest_id=self.contest.id)
        can_unregister = False
        if participant:
            can_unregister = self.can_unregister(request, participant)
        context = {
            'form': form,
            'participant': participant,
            'can_unregister': can_unregister,
            'contest_name': self.contest.name,
        }
        return TemplateResponse(request, self.registration_template, context)

    def mixins_for_admin(self):
        from oioioi.participants.admin import TermsAcceptedPhraseAdminMixin

        return super(MPRegistrationController, self).mixins_for_admin() + (
            TermsAcceptedPhraseAdminMixin,
        )

    def can_change_terms_accepted_phrase(self, request):
        return not MPRegistration.objects.filter(
            participant__contest=request.contest
        ).exists()


class MP2025RegistrationController(MPRegistrationController):
    @property
    def form_class(self):
        from oioioi.mp.forms import MP2025RegistrationForm

        return MP2025RegistrationForm


class MPContestController(ProgrammingContestController):
    description = _("Master of Programming")
    create_forum = False
    scoring_description = _(
        "The submissions are scored from 0 to 100 points.\n"
        "The participant can submit to finished rounds, but a multiplier is applied to the score of such submissions."
        )

    show_email_in_participants_data = True

    def registration_controller(self):
        return MPRegistrationController(self.contest)

    def ranking_controller(self):
        return MPRankingController(self.contest)

    def _get_score_for_submission(self, submission, ssm):
        score = FloatScore(submission.score.value)
        rtimes = self.get_round_times(None, submission.problem_instance.round)
        # Round was active when the submission was sent
        if rtimes.is_active(submission.date):
            return score
        # Round was over when the submission was sent but multiplier was ahead
        if ssm and ssm.end_date >= submission.date:
            return score * ssm.multiplier
        return None

    def update_user_result_for_problem(self, result):
        """Submissions sent during the round are scored as normal.
        Submissions sent while the round was over but SubmissionScoreMultiplier was active
        are scored with given multiplier.
        """
        submissions = Submission.objects.filter(
            problem_instance=result.problem_instance,
            user=result.user,
            kind='NORMAL',
            score__isnull=False,
        )

        best_submission = None
        best_submission_score = None
        try:
            ssm = SubmissionScoreMultiplier.objects.get(
                contest=result.problem_instance.contest
            )
        except SubmissionScoreMultiplier.DoesNotExist:
            ssm = None

        for submission in submissions:
            score = self._get_score_for_submission(submission, ssm)
            if not best_submission or (score and best_submission_score < score):
                best_submission = submission
                best_submission_score = score

        try:
            report = SubmissionReport.objects.get(
                submission=best_submission, status='ACTIVE', kind='NORMAL'
            )
        except SubmissionReport.DoesNotExist:
            report = None

        result.score = best_submission_score
        result.status = best_submission.status if best_submission else None
        result.submission_report = report

    def can_submit(self, request, problem_instance, check_round_times=True):
        """Contest admin can always submit.
        Participant can submit if:
        a. round is active
        OR
        b. SubmissionScoreMultiplier exists and it's end_time is ahead
        """
        if request.user.is_anonymous:
            return False
        if request.user.has_perm('contests.contest_admin', self.contest):
            return True
        if not is_participant(request):
            return False
        if problem_instance.round is None:
            return False

        rtimes = self.get_round_times(None, problem_instance.round)
        round_over_contest_running = rtimes.is_past(
            request.timestamp
        ) and SubmissionScoreMultiplier.objects.filter(
            contest=problem_instance.contest,
            end_date__gte=request.timestamp,
        )
        return (
            super(MPContestController, self).can_submit(
                request, problem_instance, check_round_times
            )
            or round_over_contest_running
        )


class MPRankingController(DefaultRankingController):
    """Changes to Default Ranking:
    1. Rounds with earlier start_date are more to the left.
    2. Users with 0 points aren't listed.
    """

    description = _("MP style ranking")

    def _iter_rounds(self, can_see_all, timestamp, partial_key, request=None):
        ccontroller = self.contest.controller
        queryset = self.contest.round_set.all().order_by("-start_date")
        if partial_key != CONTEST_RANKING_KEY:
            queryset = queryset.filter(id=partial_key).order_by("-start_date")
        for round in queryset:
            times = ccontroller.get_round_times(request, round)
            if can_see_all or times.public_results_visible(timestamp):
                yield round

    def _filter_pis_for_ranking(self, partial_key, queryset):
        return queryset.order_by("-round__start_date")

    def _allow_zero_score(self):
        return False


class MP2024ContestController(MPContestController):
    description = _("Master of Programming 2024")

    def update_user_result_for_problem(self, result):
        submissions = Submission.objects.filter(
            problem_instance=result.problem_instance,
            user=result.user,
            kind='NORMAL',
            score__isnull=False,
        ).order_by('score', 'date')

        if not submissions.exists():
            result.score = None
            result.status = None
            result.submission_report = None
            return

        submissions_during_round = submissions.filter(
            date__lte=result.problem_instance.round.end_date,
        ).order_by('score', 'date')

        best_score_during_round = 0
        if submissions_during_round.exists():
            best_score_during_round = submissions_during_round.last().score.value

        best_submission_overall = submissions.last()

        try:
            multiplier = SubmissionScoreMultiplier.objects.get(
                contest=result.problem_instance.contest,
            ).multiplier
        except SubmissionScoreMultiplier.DoesNotExist:
            multiplier = 0

        best_score = (
            best_score_during_round
            + (best_submission_overall.score.value - best_score_during_round)
            * multiplier
        )

        try:
            report = SubmissionReport.objects.get(
                submission=best_submission_overall,
                status='ACTIVE',
                kind='NORMAL',
            )
        except SubmissionReport.DoesNotExist:
            report = None

        result.score = FloatScore(best_score)
        result.status = best_submission_overall.status
        result.submission_report = report


class MP2025ContestController(MP2024ContestController):
    description = _("Master of Programming 2025")

    def fill_evaluation_environ(self, environ, submission):
        super(MPContestController, self).fill_evaluation_environ(environ, submission)

        environ['group_scorer'] = 'oioioi.programs.utils.min_group_scorer'
        environ['test_scorer'] = 'oioioi.programs.utils.threshold_linear_test_scorer'

    def registration_controller(self):
        return MP2025RegistrationController(self.contest)
