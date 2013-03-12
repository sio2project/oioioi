from datetime import timedelta
from django.core.exceptions import PermissionDenied
from django.template.context import RequestContext
from django.template.loader import render_to_string
from oioioi.contests.models import Submission
from oioioi.contests.controllers import submission_template_context
from oioioi.programs.controllers import ProgrammingProblemController, \
    ProgrammingContestController
from oioioi.scoresreveal.utils import has_scores_reveal, is_revealed
from oioioi.scoresreveal.models import ScoreReveal


class ScoresRevealProblemControllerMixin(object):
    def mixins_for_admin(self):
        from oioioi.scoresreveal.admin import \
            ScoresRevealProgrammingProblemAdminMixin
        return super(ScoresRevealProblemControllerMixin, self) \
            .mixins_for_admin() + (ScoresRevealProgrammingProblemAdminMixin,)

ProgrammingProblemController.mix_in(ScoresRevealProblemControllerMixin)

class ScoresRevealContestControllerMixin(object):
    def can_see_submission_score(self, request, submission):
        return super(ScoresRevealContestControllerMixin, self) \
            .can_see_submission_score(request, submission) or \
            is_revealed(submission)

    def reveal_score(self, request, submission):
        assert has_scores_reveal(submission.problem)

        if not self.can_reveal(request, submission):
            raise PermissionDenied
        ScoreReveal.objects.get_or_create(submission=submission)

    def get_revealed_submissions(self, user, problem_instance):
        return Submission.objects.filter(user=user,
             problem_instance=problem_instance,
             revealed__isnull=False)

    def get_scores_reveals_disable_time(self, problem_instance):
        return problem_instance.problem.scores_reveal_config.disable_time

    def get_scores_reveals_limit(self, problem_instance):
        return problem_instance.problem.scores_reveal_config.reveal_limit

    def is_scores_reveals_limit_reached(self, user, problem_instance):
        return self.get_revealed_submissions(user, problem_instance).count() \
               >= self.get_scores_reveals_limit(problem_instance)

    def can_reveal(self, request, submission):
        pi = submission.problem_instance
        rtimes = self.get_round_times(request, pi.round)
        return rtimes.is_active(request.timestamp) \
            and not self.is_scores_reveals_limit_reached(request.user, pi) \
            and not self.is_scores_reveals_disabled(request, pi) \
            and submission.status != 'CE' \
            and submission.user is not None \
            and request.user == submission.user \
            and not super(ScoresRevealContestControllerMixin, self). \
                can_see_submission_score(request, submission)

    def is_scores_reveals_disabled(self, request, problem_instance):
        disable_time = self.get_scores_reveals_disable_time(problem_instance) \
            or 0
        round = problem_instance.round

        rtimes = self.get_round_times(request, round)
        return rtimes.is_past(request.timestamp +
                              timedelta(minutes=disable_time)) \
            and rtimes.is_active(request.timestamp)

    def render_submission_footer(self, request, submission):
        super_footer = super(ScoresRevealContestControllerMixin, self). \
                render_submission_footer(request, submission)

        if not has_scores_reveal(submission.problem) or \
                submission.kind != 'NORMAL' or submission.user is None:
            return super_footer

        scores_reveals = self.get_revealed_submissions(submission.user,
            submission.problem_instance).count()
        scores_reveals_limit = self.get_scores_reveals_limit(
            submission.problem_instance)
        scores_reveals_disable_time = self.get_scores_reveals_disable_time(
            submission.problem_instance)
        is_scores_reveals_limit_reached = self.is_scores_reveals_limit_reached(
            submission.user, submission.problem_instance)
        can_reveal = self.can_reveal(request, submission)

        return render_to_string('scoresreveal/submission_footer.html',
            context_instance=RequestContext(request,
                {'submission': submission_template_context(request,
                 submission.programsubmission),
                 'scores_reveals': scores_reveals,
                 'scores_reveals_limit': scores_reveals_limit,
                 'scores_reveals_disable_time': scores_reveals_disable_time,
                 'can_reveal': can_reveal,
                 'is_scores_reveals_limit_reached':
                     is_scores_reveals_limit_reached,
                 'is_reveal_disabled': self.is_scores_reveals_disabled(
                     request, submission.problem_instance)})) + super_footer

ProgrammingContestController.mix_in(ScoresRevealContestControllerMixin)
