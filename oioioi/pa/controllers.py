# pylint: disable=E1103
# Instance of 'PARegistrationForm' has no 'is_valid' member
from django.shortcuts import redirect
from django.template.response import TemplateResponse
from django.utils.translation import ugettext_lazy as _

from oioioi.base.utils.redirect import safe_redirect
from oioioi.contests.utils import all_public_results_visible
from oioioi.programs.controllers import ProgrammingContestController
from oioioi.participants.controllers import ParticipantsController
from oioioi.participants.models import Participant
from oioioi.participants.utils import is_participant
from oioioi.rankings.controllers import DefaultRankingController, \
        CONTEST_RANKING_KEY
from oioioi.spliteval.controllers import SplitEvalContestControllerMixin
from oioioi.pa.models import PAProblemInstanceData
from oioioi.pa.score import PAScore


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

    def allow_login_as_public_name(self):
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
        environ['test_scorer'] = 'oioioi.pa.utils.pa_test_scorer'

        super(PAContestController, self) \
                .fill_evaluation_environ(environ, submission)

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

    def can_see_publicsolutions(self, request, round):
        return all_public_results_visible(request)

    def solutions_must_be_public(self, qs):
        return qs

    def process_uploaded_problem(self, problem, problem_instance, is_new=True):
        if is_new:
            PAProblemInstanceData.objects.create(
                    problem_instance=problem_instance, division='NONE')
PAContestController.mix_in(SplitEvalContestControllerMixin)


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

    def _rounds_for_ranking(self, request, key=CONTEST_RANKING_KEY):
        if key not in [A_PLUS_B_RANKING_KEY, B_RANKING_KEY]:
            return super(PARankingController, self)._rounds_for_ranking(
                request, key)
        else:
            rounds = super(PARankingController, self)._rounds_for_ranking(
                request, CONTEST_RANKING_KEY)
            return (r for r in rounds if not r.is_trial)

    def available_rankings(self, request):
        rankings = [(A_PLUS_B_RANKING_KEY, _("Division A + B")),
                (B_RANKING_KEY, _("Division B"))]
        for round in self._rounds_for_ranking(request):
            if round.is_trial:
                rankings.append((str(round.id), round.name))
        return rankings

    def _filter_pis_for_ranking(self, key, queryset):
        if key == A_PLUS_B_RANKING_KEY:
            return queryset.filter(
                    paprobleminstancedata__division__in=['A', 'B'])
        elif key == B_RANKING_KEY:
            return queryset.filter(paprobleminstancedata__division='B')
        else:
            return queryset.filter(paprobleminstancedata__division='NONE')

    def _allow_zero_score(self):
        return False
