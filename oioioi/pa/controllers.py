import datetime
import logging

from django import forms
from django.db.models import Q
from django.shortcuts import redirect
from django.template.response import TemplateResponse
from django.utils.translation import gettext_lazy as _

from oioioi.acm.controllers import ACMContestController
from oioioi.base.utils.query_helpers import Q_always_true
from oioioi.base.utils.redirect import safe_redirect
from oioioi.contests.utils import (
    all_non_trial_public_results_visible,
    is_contest_admin,
    is_contest_observer,
)
from oioioi.pa.models import PAProblemInstanceData, PARegistration
from oioioi.pa.score import PAScore
from oioioi.participants.controllers import (
    OnsiteContestControllerMixin,
    ParticipantsController,
)
from oioioi.participants.models import Participant
from oioioi.participants.utils import is_participant
from oioioi.programs.controllers import ProgrammingContestController
from oioioi.rankings.controllers import CONTEST_RANKING_KEY, DefaultRankingController
from oioioi.contests.models import RegistrationStatus


auditLogger = logging.getLogger(__name__ + ".audit")


class PARegistrationController(ParticipantsController):
    registration_template = 'pa/registration.html'

    @property
    def form_class(self):
        from oioioi.pa.forms import PARegistrationForm

        return PARegistrationForm

    @property
    def participant_admin(self):
        from oioioi.pa.admin import PARegistrationParticipantAdmin

        return PARegistrationParticipantAdmin

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

    def can_unregister(self, request, participant):
        return False

    def registration_view(self, request):

        registration_status = self.get_registration_status(request)
        if registration_status == RegistrationStatus.NOT_OPEN_YET:
            return TemplateResponse(request, 'contests/registration_not_open_yet.html')

        participant = self._get_participant_for_form(request)

        if 'pa_paregistrationformdata' in request.session:
            # pylint: disable=not-callable
            form = self.form_class(request.session['pa_paregistrationformdata'])
            del request.session['pa_paregistrationformdata']
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
                auditLogger.info(
                    "User %d (%s) registered in %s from IP %s UA: %s",
                    request.user.id,
                    request.user.username,
                    self.contest.id,
                    request.META.get('REMOTE_ADDR', '?'),
                    request.headers.get('user-agent', '?'),
                )
                if 'next' in request.GET:
                    return safe_redirect(request, request.GET['next'])
                else:
                    return redirect('default_contest_view', contest_id=self.contest.id)

        context = {'form': form, 'participant': participant}
        return TemplateResponse(request, self.registration_template, context)

    def mixins_for_admin(self):
        from oioioi.participants.admin import TermsAcceptedPhraseAdminMixin

        return super(PARegistrationController, self).mixins_for_admin() + (
            TermsAcceptedPhraseAdminMixin,
        )

    def can_change_terms_accepted_phrase(self, request):
        return not PARegistration.objects.filter(
            participant__contest=request.contest
        ).exists()


class PAContestController(ProgrammingContestController):
    description = _("Algorithmic Engagements")
    create_forum = True
    scoring_description = _(
        "The submissions are judged on real-time. All problems have 10 test groups, each worth 1 point. "
        "If any of the tests in a group fails, the group is worth 0 points.\n"
        "The full scoring is available after the end of the round."
        "The ranking is determined by the total score and number of 10-score submissions, 9-score, 8-score etc."
        )

    def fill_evaluation_environ(self, environ, submission):
        environ['test_scorer'] = 'oioioi.pa.utils.pa_test_scorer'

        super(PAContestController, self).fill_evaluation_environ(environ, submission)

    def update_user_result_for_problem(self, result):
        super(PAContestController, self).update_user_result_for_problem(result)
        if result.score is not None:
            result.score = PAScore(result.score)

    def registration_controller(self):
        return PARegistrationController(self.contest)

    def ranking_controller(self):
        return PARankingController(self.contest)

    def separate_public_results(self):
        return True

    def can_submit(self, request, problem_instance, check_round_times=True):
        if request.user.is_anonymous:
            return False
        if request.user.has_perm('contests.contest_admin', self.contest):
            return True
        if not is_participant(request):
            return False
        return super(PAContestController, self).can_submit(
            request, problem_instance, check_round_times
        )

    def can_see_publicsolutions(self, request, round):
        if all_non_trial_public_results_visible(request):
            # Do not show solutions for trial rounds that has future
            # publication date (e.g. not set).
            return self.get_round_times(request, round).public_results_visible(
                request.timestamp
            )
        return False

    def solutions_must_be_public(self, qs):
        return qs.filter(
            user__isnull=False,
            user__is_superuser=False,
            submissionreport__userresultforproblem__isnull=False,
        )

    def get_division_choices(self):
        return [('A', _("A")), ('B', _("B")), ('NONE', _("None"))]

    def adjust_upload_form(self, request, existing_problem, form):
        super(PAContestController, self).adjust_upload_form(
            request, existing_problem, form
        )
        initial = 'NONE'
        if existing_problem:
            try:
                initial = PAProblemInstanceData.objects.get(
                    problem_instance__problem=existing_problem
                ).division
            except PAProblemInstanceData.DoesNotExist:
                pass

        form.fields['division'] = forms.ChoiceField(
            required=True,
            label=_("Division"),
            initial=initial,
            choices=self.get_division_choices(),
        )

    def fill_upload_environ(self, request, form, env):
        super(PAContestController, self).fill_upload_environ(request, form, env)
        env['division'] = form.cleaned_data['division']
        env['post_upload_handlers'] += ['oioioi.pa.handlers.save_division']

    def get_default_safe_exec_mode(self):
        return 'cpu'

    def get_allowed_languages(self):
        return ['C', 'C++', 'Pascal', 'Java']


A_PLUS_B_RANKING_KEY = 'ab'
B_RANKING_KEY = 'b'


class PARankingController(DefaultRankingController):
    """Problems in a PA style contest are divided into two divisions
    (``A`` and ``B``). It is also possible to set a problem's division to
    ``None``.

    There are three types of rankings in a PA style contest.

    1) Trial round ranking. The key (the id) of such a ranking is the id of
       some trial round (there may be more than one trial round in a
       contest). Problems displayed in the ranking are the problems
       attached to the round whose division is set to ``None``.

    2) Division ``B`` ranking (key = ``B_RANKING_KEY``). It consists
       of all problems from non-trial rounds whose division is set to ``B``.

    3) ``A + B`` ranking (key = ``A_PLUS_B_RANKING_KEY``). It consists of
       problems from both divisions and from all non-trial rounds.

    Note that if a problem belongs to ``A`` or ``B`` and is attached to a
    trial round, it won't belong to any ranking. The same applies to
    problems in non-trial rounds with division set to ``None``.
    """

    description = _("PA style ranking")

    def _rounds_for_ranking(self, request, partial_key=CONTEST_RANKING_KEY):
        method = super(PARankingController, self)._rounds_for_ranking
        if partial_key not in [A_PLUS_B_RANKING_KEY, B_RANKING_KEY]:
            return method(request, partial_key)
        else:
            rounds = method(request, CONTEST_RANKING_KEY)
            return (r for r in rounds if not r.is_trial)

    def _rounds_for_key(self, key):
        method = super(PARankingController, self)._rounds_for_key
        partial_key = self.get_partial_key(key)
        if partial_key not in [A_PLUS_B_RANKING_KEY, B_RANKING_KEY]:
            return method(key)
        else:
            rounds = method(self.replace_partial_key(key, CONTEST_RANKING_KEY))
            return (r for r in rounds if not r.is_trial)

    def available_rankings(self, request):
        rankings = [
            (A_PLUS_B_RANKING_KEY, _("Division A + B")),
            (B_RANKING_KEY, _("Division B")),
        ]
        for round in self._rounds_for_ranking(request):
            if round.is_trial:
                rankings.append((str(round.id), round.name))
        return rankings

    def _filter_pis_for_ranking(self, partial_key, queryset):
        if partial_key == A_PLUS_B_RANKING_KEY:
            return queryset.filter(paprobleminstancedata__division__in=['A', 'B'])
        elif partial_key == B_RANKING_KEY:
            return queryset.filter(paprobleminstancedata__division='B')
        else:
            return queryset.filter(paprobleminstancedata__division='NONE')

    def _allow_zero_score(self):
        return False


class PADivCRankingController(PARankingController):
    description = _("PA style ranking (with division C)")

    def available_rankings(self, request):
        rankings = [(A_PLUS_B_RANKING_KEY, _("Division A + B + C")),
                (B_RANKING_KEY, _("Division B + C"))]
        for round in self._rounds_for_ranking(request):
            if round.is_trial:
                rankings.append((str(round.id), round.name))
        return rankings

    def _filter_pis_for_ranking(self, partial_key, queryset):
        if partial_key == A_PLUS_B_RANKING_KEY:
            return queryset.filter(
                    paprobleminstancedata__division__in=['A', 'B', 'C'])
        elif partial_key == B_RANKING_KEY:
            return queryset.filter(paprobleminstancedata__division__in=['B', 'C'])
        else:
            return queryset.filter(paprobleminstancedata__division='NONE')


class PAFinalsContestController(ACMContestController):
    description = _("Algorithmic Engagements finals")
    scoring_description = _(
        "The solutions are judged on real-time. "
        "The submission is correct if it passes all the test cases.\n"
        "Participants are ranked by the number of solved problems. "
        "In case of a tie, the times of first correct submissions are summed up and a penalty of 20 minutes is added for each incorrect submission.\n"
        "The lower the total time, the higher the rank.\n"
        "Compilation errors and system errors are not considered as an incorrect submission.\n"
        "The ranking is frozen 15 minutes before the end of the trial rounds and 60 minutes before the end of the normal rounds."
        )

    def registration_controller(self):
        return ParticipantsController(self.contest)

    def can_print_files(self, request):
        return True

    def can_see_livedata(self, request):
        return True

    def is_onsite(self):
        return True

    def default_can_see_ranking(self, request):
        return is_contest_admin(request) or is_contest_observer(request)

    def get_round_freeze_time(self, round):
        if not round.end_date:
            return None
        if round.is_trial:
            frozen_ranking_minutes = 15
        else:
            frozen_ranking_minutes = 60

        return round.end_date - datetime.timedelta(minutes=frozen_ranking_minutes)

    def get_safe_exec_mode(self):
        return 'cpu'


PAFinalsContestController.mix_in(OnsiteContestControllerMixin)

class PADivCContestController(PAContestController):
    description = _("Algorithmic Engagements with Division C")

    def ranking_controller(self):
        return PADivCRankingController(self.contest)

    def get_division_choices(self):
        return [('A', _("A")), ('B', _("B")), ('C', _("C")), ('NONE', _("None"))]
