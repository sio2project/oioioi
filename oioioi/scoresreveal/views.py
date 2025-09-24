from django.contrib import messages
from django.http import Http404
from django.shortcuts import redirect
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_POST

from oioioi.base.permissions import enforce_condition
from oioioi.contests.utils import (
    can_enter_contest,
    contest_exists,
    get_submission_or_error,
)
from oioioi.scoresreveal.utils import has_scores_reveal


@enforce_condition(contest_exists & can_enter_contest)
@require_POST
def score_reveal_view(request, submission_id):
    submission = get_submission_or_error(request, submission_id)
    controller = request.contest.controller
    if not has_scores_reveal(submission.problem_instance):
        raise Http404
    decision, reason = controller.can_reveal(request, submission)
    if not decision:
        messages.error(request, reason)
    else:
        controller.reveal_score(request, submission)
        messages.success(request, _("Submission score has been revealed."))

    return redirect(
        "submission",
        contest_id=submission.problem_instance.contest_id,
        submission_id=submission.id,
    )
