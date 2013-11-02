from django.contrib import messages
from django.shortcuts import redirect, get_object_or_404
from django.template.response import TemplateResponse
from django.utils.translation import ngettext
from django.utils.translation import ugettext_lazy as _
from django.views.decorators.http import require_POST

from oioioi.base.permissions import enforce_condition
from oioioi.contests.utils import contest_exists, is_contest_admin
from oioioi.similarsubmits.forms import BulkAddSubmissionsSimilarityForm
from oioioi.similarsubmits.models import SubmissionsSimilarityGroup, \
        SubmissionsSimilarityEntry
from oioioi.similarsubmits.utils import is_correct_submissionssimilarity


@enforce_condition(contest_exists & is_contest_admin)
def bulk_add_similarities_view(request, contest_id):
    if request.method == 'POST':
        form = BulkAddSubmissionsSimilarityForm(request, request.POST)
        if form.is_valid():
            groups = form.cleaned_data['similar_groups']
            for group in groups:
                entries = SubmissionsSimilarityEntry.objects.filter(
                        submission_in=group).select_related('group')

                if entries.exists():
                    groups = set([entry.group for entry in entries])
                    group_model = next(iter(groups))
                    groups -= group_model
                    # If group contains submissions from multiple existing
                    # groups then merge all of them.
                    for g in groups:
                        for e in g.submissions:
                            e.group = group_model
                        g.delete()
                else:
                    group_model = SubmissionsSimilarityGroup(
                            contest=request.contest)
                    group_model.save()

                for submission in group:
                    SubmissionsSimilarityEntry.objects.get_or_create(
                            group=group_model, submission=submission).save()

            messages.success(request,
                             ngettext("Created one group",
                                      "Created %d groups" % len(groups),
                                      len(groups)))
            return redirect(
                'oioioiadmin:similarsubmits_'
                'submissionssimilaritygroup_changelist')
    else:
        form = BulkAddSubmissionsSimilarityForm(request)
    return TemplateResponse(request, 'similarsubmits/bulk_add.html',
            {'form': form})


@require_POST
@enforce_condition(contest_exists & is_contest_admin)
@enforce_condition(is_correct_submissionssimilarity)
def mark_guilty_view(request, contest_id, entry_id):
    entry = get_object_or_404(SubmissionsSimilarityEntry, id=entry_id)

    if entry.submission.kind == 'IGNORED_HIDDEN':
        messages.error(request, _("You can't mark a removed submission as"
                                  " guilty because the author will not be able"
                                  " to see it."))
    else:
        entry.guilty = True
        entry.save()

    return redirect('submission',
            contest_id=contest_id, submission_id=entry.submission_id)


@require_POST
@enforce_condition(contest_exists & is_contest_admin)
@enforce_condition(is_correct_submissionssimilarity)
def mark_not_guilty_view(request, contest_id, entry_id):
    entry = get_object_or_404(SubmissionsSimilarityEntry, id=entry_id)
    entry.guilty = False
    entry.save()
    return redirect('submission',
        contest_id=contest_id, submission_id=entry.submission_id)
