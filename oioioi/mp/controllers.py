from django.shortcuts import redirect
from django.template.loader import render_to_string
from django.template.response import TemplateResponse
from django.utils.translation import gettext_lazy as _

from oioioi.base.utils.query_helpers import Q_always_true
from oioioi.base.utils.redirect import safe_redirect
from oioioi.contests.models import Submission
from oioioi.mp.models import MPRegistration, SubmissionScoreMultiplier
from oioioi.mp.score import FloatScore
from oioioi.participants.controllers import ParticipantsController
from oioioi.participants.models import Participant
from oioioi.participants.utils import is_participant
from oioioi.programs.controllers import ProgrammingContestController
from oioioi.rankings.controllers import DefaultRankingController

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

    def registration_view(self, request):
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


class MPContestController(ProgrammingContestController):
    description = _("Master of Programming")
    create_forum = False

    show_email_in_participants_data = True

    def registration_controller(self):
        return MPRegistrationController(self.contest)

    def ranking_controller(self):
        return MPRankingController(self.contest)

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

        if submissions:
            best_submission = None
            for submission in submissions:
                ssm = SubmissionScoreMultiplier.objects.filter(
                    contest=submission.problem_instance.contest,
                )

                score = FloatScore(submission.score.value)
                rtimes = self.get_round_times(None, submission.problem_instance.round)
                if rtimes.is_active(submission.date):
                    pass
                elif ssm.exists() and ssm[0].end_date >= submission.date:
                    score = score * ssm[0].multiplier
                else:
                    score = None
                if not best_submission or (
                    score is not None and best_submission[1] < score
                ):
                    best_submission = [submission, score]

            result.score = best_submission[1]
            result.status = best_submission[0].status

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
    1. Sum column is just after User column
    2. Rounds with earlier start_date are more to the left
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

    def _render_ranking_page(self, key, data, page):
        request = self._fake_request(page)
        data['is_admin'] = self.is_admin_key(key)
        return render_to_string('mp/ranking.html', context=data, request=request)

    def _allow_zero_score(self):
        return False
