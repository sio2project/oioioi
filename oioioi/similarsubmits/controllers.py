from django.db.models import Q
from django.template.loader import render_to_string

from oioioi.contests.controllers import submission_template_context
from oioioi.contests.models import Submission
from oioioi.contests.utils import is_contest_admin
from oioioi.programs.controllers import ProgrammingContestController
from oioioi.similarsubmits.models import (
    SubmissionsSimilarityEntry,
    SubmissionsSimilarityGroup,
)


class SimilarityDisqualificationMixin(object):
    """ContestController mixin that sets up similarsubmits app."""

    def is_submission_disqualified(self, submission):
        prev = super(SimilarityDisqualificationMixin, self).is_submission_disqualified(
            submission
        )

        return (
            prev
            or SubmissionsSimilarityEntry.objects.filter(
                submission=submission, guilty=True
            ).exists()
        )

    def has_disqualification_history(self, submission):
        prev = super(
            SimilarityDisqualificationMixin, self
        ).has_disqualification_history(submission)
        return (
            prev
            or SubmissionsSimilarityEntry.objects.filter(submission=submission).exists()
        )

    def is_any_submission_to_problem_disqualified(self, user, problem_instance):
        prev = super(
            SimilarityDisqualificationMixin, self
        ).is_any_submission_to_problem_disqualified(user, problem_instance)

        return (
            prev
            or SubmissionsSimilarityEntry.objects.filter(
                submission__problem_instance=problem_instance.id,
                submission__user=user.id,
            )
            .filter(guilty=True)
            .exists()
        )

    def is_user_disqualified(self, request, user):
        prev = super(SimilarityDisqualificationMixin, self).is_user_disqualified(
            request, user
        )

        return (
            prev
            or SubmissionsSimilarityEntry.objects.filter(
                submission__problem_instance__contest=request.contest,
                submission__user=user,
            )
            .filter(guilty=True)
            .exists()
        )

    def user_has_disqualification_history(self, request, user):
        prev = super(
            SimilarityDisqualificationMixin, self
        ).user_has_disqualification_history(request, user)

        return (
            prev
            or SubmissionsSimilarityEntry.objects.filter(
                submission__problem_instance__contest=request.contest,
                submission__user=user,
            ).exists()
        )

    def change_submission_kind(self, submission, kind):
        old_kind = submission.kind
        super(SimilarityDisqualificationMixin, self).change_submission_kind(
            submission, kind
        )
        if submission.kind != old_kind:
            SubmissionsSimilarityEntry.objects.filter(submission=submission).update(
                guilty=False
            )

    def exclude_disqualified_users(self, queryset):
        return (
            super(SimilarityDisqualificationMixin, self)
            .exclude_disqualified_users(queryset)
            .exclude(
                submission__in=Submission.objects.filter(
                    similarities__guilty=True, problem_instance__contest=self.contest
                )
            )
        )

    def filter_visible_sources(self, request, queryset):
        prev = (
            super(SimilarityDisqualificationMixin, self)
            .filter_visible_sources(request, queryset)
            .distinct()
        )

        if not request.user.is_authenticated:
            return prev

        # TODO: only in grace period, guilty
        # Do not split this filter as it spans many-to-many relationship
        similar = queryset.filter(
            similarities__group__submissions__submission__user=request.user,
            similarities__group__submissions__guilty=True,
        ).distinct()
        return (prev | similar).distinct()

    def _render_disqualification_reason(self, request, submission):
        prev = super(
            SimilarityDisqualificationMixin, self
        )._render_disqualification_reason(request, submission)

        if is_contest_admin(request):
            q_expression = Q(submissions__submission=submission)
        else:
            # Do not split this filter as it spans many-to-many relationship
            q_expression = Q(
                submissions__submission=submission, submissions__guilty=True
            )
        similarities = SubmissionsSimilarityGroup.objects.filter(
            q_expression
        ).prefetch_related('submissions')
        if not similarities:
            return prev

        submission_contexts = {}
        for group in similarities:
            for entry in group.submissions.all():
                submission_contexts[entry.submission] = submission_template_context(
                    request, entry.submission, skip_valid_kinds=True
                )

        template = (
            'similarsubmits/programming_similar_submissions_admin.html'
            if is_contest_admin(request)
            else 'similarsubmits/programming_similar_submissions.html'
        )

        context = {
            'similarities': similarities,
            'main_submission_id': submission.id,
            'submission_contexts': submission_contexts,
        }

        return prev + render_to_string(template, request=request, context=context)


ProgrammingContestController.mix_in(SimilarityDisqualificationMixin)
