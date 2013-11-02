from oioioi.base.permissions import make_condition
from oioioi.similarsubmits.models import SubmissionsSimilarityEntry


@make_condition()
def is_correct_submissionssimilarity(request, *args, **kwargs):
    entry_id = kwargs.get('entry_id')

    if not entry_id:
        return False

    return SubmissionsSimilarityEntry.objects \
            .filter(id=entry_id, group__contest=request.contest).exists()
