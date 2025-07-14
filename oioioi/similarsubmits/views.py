from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.template.response import TemplateResponse
from django.utils.translation import gettext_lazy as _
from django.utils.translation import ngettext_lazy
from django.views.decorators.http import require_POST

from oioioi.base.permissions import enforce_condition
from oioioi.contests.utils import contest_exists, is_contest_admin
from oioioi.similarsubmits.forms import BulkAddSubmissionsSimilarityForm
from oioioi.similarsubmits.models import (
    SubmissionsSimilarityEntry,
    SubmissionsSimilarityGroup,
)
from oioioi.similarsubmits.utils import is_correct_submissionssimilarity


@enforce_condition(contest_exists & is_contest_admin)
def bulk_add_similarities_view(request):
    if request.method == "POST":
        form = BulkAddSubmissionsSimilarityForm(request, request.POST)
        if form.is_valid():
            groups = form.cleaned_data["similar_groups"]
            for group in groups:
                entries = SubmissionsSimilarityEntry.objects.filter(submission__in=group).select_related("group")

                if entries.exists():
                    groups = set([entry.group for entry in entries])
                    group_model = groups.pop()
                    # If group contains submissions from multiple existing
                    # groups then merge all of them.
                    for g in groups:
                        for e in g.submissions.all():
                            e.group = group_model
                            e.save()
                        g.delete()
                else:
                    group_model = SubmissionsSimilarityGroup(contest=request.contest)
                    group_model.save()

                for submission in group:
                    SubmissionsSimilarityEntry.objects.get_or_create(group=group_model, submission=submission)

            messages.success(
                request,
                ngettext_lazy("Created one group", "Created %(groups_count)d groups", len(groups)) % {"groups_count": len(groups)},
            )
            return redirect("oioioiadmin:similarsubmits_submissionssimilaritygroup_changelist")
    else:
        form = BulkAddSubmissionsSimilarityForm(request)
    return TemplateResponse(request, "similarsubmits/bulk_add.html", {"form": form})


@require_POST
@enforce_condition(contest_exists & is_contest_admin)
@enforce_condition(is_correct_submissionssimilarity)
def mark_guilty_view(request, entry_id):
    entry = get_object_or_404(SubmissionsSimilarityEntry, id=entry_id)

    if entry.submission.kind == "IGNORED_HIDDEN":
        messages.error(
            request,
            _("You can't mark a removed submission as guilty because the author will not be able to see it."),
        )
    else:
        entry.guilty = True
        entry.save()

    return redirect("submission", contest_id=request.contest.id, submission_id=entry.submission_id)


@require_POST
@enforce_condition(contest_exists & is_contest_admin)
@enforce_condition(is_correct_submissionssimilarity)
def mark_not_guilty_view(request, entry_id):
    entry = get_object_or_404(SubmissionsSimilarityEntry, id=entry_id)
    entry.guilty = False
    entry.save()
    return redirect("submission", contest_id=request.contest.id, submission_id=entry.submission_id)
