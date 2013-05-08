from datetime import timedelta
from django.template.context import RequestContext
from django.template.loader import render_to_string
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _, ungettext_lazy
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
        assert self.can_reveal(request, submission)[0]

        obj, created = ScoreReveal.objects.get_or_create(submission=submission)
        return created

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
        """Checks if given submission can be revealed by provided request.

           Returns tuple (True, None) or (False, reason)
           where reason is a string containing the reason of denying access.
        """
        pi = submission.problem_instance
        rtimes = self.get_round_times(request, pi.round)
        if not rtimes.is_active(request.timestamp):
            return False, _("The round is not active.")
        if request.user != submission.user:
            return False, _("Only author can reveal the submission score.")
        if self.is_scores_reveals_limit_reached(request.user, pi):
            return False, _("You have already reached the reveals limit.")
        if self.is_scores_reveals_disabled(request, pi):
            minutes_disabled = self.get_scores_reveals_disable_time(
                submission.problem_instance)
            return False, \
                mark_safe(ungettext_lazy(
                    "Scores revealing is disabled during the last "
                    "<strong>minute</strong> of the round.",
                    "Scores revealing is disabled during the last "
                    "<strong>%(scores_reveals_disable_time)d</strong> "
                    "minutes of the round.",
                    minutes_disabled) %
                    {'scores_reveals_disable_time': minutes_disabled})
        if submission.status == 'CE':
            return False, _("You cannot reveal the score of the submission "
                "with status \"Compilation Error\".")
        if submission.user is None:
            return False, _("The submission author is not set.")
        if not submission.is_scored():
            return False, _("Unfortunately, this submission has not been "
                            "scored yet, so you can't see your score. "
                            "Please come back later.")
        if super(ScoresRevealContestControllerMixin, self). \
                can_see_submission_score(request, submission):
            return False, _("You already have access to the submission score.")

        return True, None

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
        can_reveal, reason = self.can_reveal(request, submission)

        return render_to_string('scoresreveal/submission_footer.html',
            context_instance=RequestContext(request,
                {'submission': submission_template_context(request,
                 submission.programsubmission),
                 'scores_reveals': scores_reveals,
                 'scores_reveals_limit': scores_reveals_limit,
                 'scores_reveals_disable_time': scores_reveals_disable_time,
                 'can_reveal': can_reveal,
                 'can_reveal_reason': reason})) + super_footer

ProgrammingContestController.mix_in(ScoresRevealContestControllerMixin)
