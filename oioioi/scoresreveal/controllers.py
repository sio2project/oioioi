from datetime import timedelta  # pylint: disable=E0611

from django.template.loader import render_to_string
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _
from django.utils.translation import ngettext_lazy

from oioioi.contests.controllers import submission_template_context
from oioioi.contests.models import Submission
from oioioi.programs.controllers import ProgrammingContestController
from oioioi.scoresreveal.models import ScoreReveal
from oioioi.scoresreveal.utils import has_scores_reveal, is_revealed


class ScoresRevealContestControllerMixin:
    """ContestController mixin that sets up scoresreveal app."""

    def can_see_submission_score(self, request, submission):
        return super().can_see_submission_score(request, submission) or is_revealed(submission) or self.is_score_auto_revealed(request, submission)

    def reveal_score(self, request, submission):
        assert has_scores_reveal(submission.problem_instance)
        assert self.can_reveal(request, submission)[0]

        ScoreReveal.objects.get_or_create(submission=submission)

    def get_revealed_submissions(self, user, problem_instance):
        return Submission.objects.filter(user=user, problem_instance=problem_instance, revealed__isnull=False)

    def get_scores_reveals_disable_time(self, problem_instance):
        return problem_instance.scores_reveal_config.disable_time

    def get_scores_reveals_limit(self, problem_instance):
        return problem_instance.scores_reveal_config.reveal_limit

    def is_scores_reveals_limit_reached(self, user, problem_instance):
        limit = self.get_scores_reveals_limit(problem_instance)
        return limit is not None and self.get_revealed_submissions(user, problem_instance).count() >= limit

    def is_auto_reveal_enabled(self, problem_instance):
        return has_scores_reveal(problem_instance) and self.get_scores_reveals_limit(problem_instance) is None

    def is_score_ready_to_be_revealed(self, request, submission):
        """Checks if given submission can be revealed, assuming that the
        reveals limit is not reached or submissions are revealed automatically.

        Returns tuple (True, None) or (False, reason)
        where reason is a string containing the reason of denying access.
        """
        if self.is_scores_reveals_disabled(request, submission):
            minutes_disabled = self.get_scores_reveals_disable_time(submission.problem_instance)
            return False, mark_safe(
                ngettext_lazy(
                    "Scores revealing is disabled during the last <strong>minute</strong> of the round.",
                    "Scores revealing is disabled during the last <strong>%(scores_reveals_disable_time)d</strong> minutes of the round.",
                    minutes_disabled,
                )
                % {"scores_reveals_disable_time": minutes_disabled}
            )
        if submission.status == "CE":
            return False, _('You cannot reveal the score of the submission with status "Compilation Error".')
        if not submission.is_scored():
            return False, _("Unfortunately, this submission has not been scored yet, so you can't see your score. Please come back later.")
        return True, None

    def is_score_auto_revealed(self, request, submission):
        return self.is_auto_reveal_enabled(submission.problem_instance) and self.is_score_ready_to_be_revealed(request, submission)[0]

    def can_reveal(self, request, submission):
        """Checks if given submission can be manually revealed by provided request.

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
        if submission.user is None:
            return False, _("The submission author is not set.")
        if self.can_see_submission_score(request, submission):
            return False, _("You already have access to the submission score.")

        return self.is_score_ready_to_be_revealed(request, submission)

    def is_scores_reveals_disabled(self, request, submission):
        problem_instance = submission.problem_instance
        disable_time = self.get_scores_reveals_disable_time(problem_instance) or 0
        round = problem_instance.round

        rtimes = self.get_round_times(request, round)
        return rtimes.is_past(submission.date + timedelta(minutes=disable_time))

    def render_submission_footer(self, request, submission):
        super_footer = super().render_submission_footer(request, submission)

        if not has_scores_reveal(submission.problem_instance) or submission.kind != "NORMAL" or submission.user is None:
            return super_footer

        scores_reveals_limit = self.get_scores_reveals_limit(submission.problem_instance)
        if scores_reveals_limit:
            scores_reveals = self.get_revealed_submissions(submission.user, submission.problem_instance).count()
        else:
            scores_reveals = None

        scores_reveals_disable_time = self.get_scores_reveals_disable_time(submission.problem_instance)

        score_visible = self.can_see_submission_score(request, submission) and submission.is_scored()
        if not score_visible:
            if scores_reveals_limit is None:
                can_reveal, reason = self.is_score_ready_to_be_revealed(request, submission)
            else:
                can_reveal, reason = self.can_reveal(request, submission)
        else:
            can_reveal, reason = None, None

        return (
            render_to_string(
                "scoresreveal/submission-footer.html",
                request=request,
                context={
                    "submission": submission_template_context(request, submission),
                    "scores_reveals": scores_reveals,
                    "scores_reveals_limit": scores_reveals_limit,
                    "scores_reveals_disable_time": scores_reveals_disable_time,
                    "score_visible": score_visible,
                    "can_reveal": can_reveal,
                    "can_reveal_reason": reason,
                },
            )
            + super_footer
        )


ProgrammingContestController.mix_in(ScoresRevealContestControllerMixin)
