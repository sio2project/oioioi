from django.contrib import messages
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_POST
from django.utils.translation import ugettext_lazy as _
from oioioi.base.permissions import enforce_condition
from oioioi.contests.models import Submission
from oioioi.contests.utils import can_enter_contest, is_contest_admin
from oioioi.contests.utils import check_submission_access
from oioioi.scoresreveal.utils import has_scores_reveal

@enforce_condition(can_enter_contest)
@require_POST
def score_reveal_view(request, contest_id, submission_id):
    submission = get_object_or_404(Submission, id=submission_id, kind='NORMAL')
    check_submission_access(request, submission)

    controller = request.contest.controller
    if not has_scores_reveal(submission.problem):
        raise Http404
    decision, reason = controller.can_reveal(request, submission)
    if not decision:
        messages.error(request, reason)
    else:
        controller.reveal_score(request, submission)
        messages.success(request, _("Submission score has been revealed."))

    return redirect('submission',
        contest_id=submission.problem_instance.contest_id,
        submission_id=submission.id)