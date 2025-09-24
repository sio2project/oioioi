from django.contrib.auth.models import User
from django.template.loader import render_to_string
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _

from oioioi.contests.controllers import ContestController, submission_template_context
from oioioi.contests.models import Submission
from oioioi.contests.utils import is_contest_admin
from oioioi.disqualification.models import Disqualification, DisqualificationsConfig
from oioioi.programs.controllers import ProgrammingContestController
from oioioi.rankings.controllers import DefaultRankingController


class DisqualificationContestControllerMixin:
    """ContestController mixin that adds a disqualification functionality to
    the contest.
    """

    def is_submission_disqualified(self, submission):
        """Decides whether the submission is currently disqualified.

        This won't automatically propagate to user disqualification.
        Used mostly with single submission context.
        """
        return Disqualification.objects.filter(submission=submission, guilty=True).exists()

    def has_disqualification_history(self, submission):
        """Should be ``True`` if the submission was disqualified anytime.

        This method is for example used to check if the disqualification
        admin panel should be displayed.
        """
        return Disqualification.objects.filter(submission=submission).exists()

    def is_any_submission_to_problem_disqualified(self, user, problem_instance):
        """Should be ``True`` if the given user has any disqualified
        submission to this problem.

        If so, this will usually result in hiding scores in other
        submissions to this problem.
        """
        return Disqualification.objects.filter(user=user, submission__problem_instance=problem_instance, guilty=True).exists()

    def is_user_disqualified(self, request, user):
        """True if the user should be considered disqualified

        The default implementation *does not* infer it from
        previous methods.
        """
        return Disqualification.objects.filter(contest=request.contest, user=user, guilty=True).exists()

    def user_has_disqualification_history(self, request, user):
        """True if the user was disqualified anytime.

        This method is for example used to check if the disqualification
        admin panel should be displayed.
        """
        return Disqualification.objects.filter(contest=request.contest, user=user).exists()

    def exclude_disqualified_users(self, queryset):
        """Filters the queryset of :class:`~django.contrib.auth.model.User`
        to select only users which are not disqualified in this contest.
        """
        return queryset.exclude(disqualification__in=Disqualification.objects.filter(contest=self.contest, guilty=True))

    def change_submission_kind(self, submission, kind):
        """Changing the kind of submission should undisqualify given submission"""
        old_kind = submission.kind
        super(DisqualificationContestControllerMixin, self).change_submission_kind(submission, kind)

        if submission.kind != old_kind:
            Disqualification.objects.filter(submission=submission).update(guilty=False)

    def _render_disqualification_reason(self, request, submission):
        """Renders part with reason of the given submission disqualification.

        This method is only used internally.
        """
        reasons = Disqualification.objects.filter(submission=submission)
        if not is_contest_admin(request):
            reasons = reasons.filter(guilty=True)

        if not reasons:
            return mark_safe("")
        return render_to_string(
            "disqualification/reason.html",
            request=request,
            context={
                "submission": submission_template_context(request, submission),
                "reasons": reasons,
            },
        )

    def _get_contest_disq_info(self):
        try:
            return DisqualificationsConfig.objects.get(contest=self.contest).info
        except DisqualificationsConfig.DoesNotExist:
            return None

    def render_submission_disqualifiaction(self, request, submission):
        """Renders the disqualification reason of the given submission to HTML."""
        reason = self._render_disqualification_reason(request, submission)
        template = "disqualification/generic.html"

        if is_contest_admin(request):
            template = "disqualification/generic-admin.html"

        return render_to_string(
            template,
            request=request,
            context={
                "submission": submission_template_context(request, submission),
                "reason": reason,
                "contest_disq_info": self._get_contest_disq_info(),
            },
        )

    def _render_contestwide_disqualification_reason(self, request, user):
        """Renders part with reason of the given user disqualification not
        directly associated with any particular submission.

        This method is only used internally.
        """
        reasons = Disqualification.objects.filter(user=user, contest=request.contest, submission__isnull=True)
        if not is_contest_admin(request):
            reasons = reasons.filter(guilty=True)

        if not reasons:
            return None
        return render_to_string(
            "disqualification/reason.html",
            request=request,
            context={"reasons": reasons},
        )

    def render_my_submissions_header(self, request, submissions):
        header = super(DisqualificationContestControllerMixin, self).render_my_submissions_header(request, submissions)
        disq_header = self.render_disqualifications(request, request.user, submissions)
        if disq_header:
            header += disq_header
        return header

    def render_disqualifications(self, request, user, submissions):
        """Renders all disqualifications of the given user to HTML, which
        may be put anywhere on the site.

        This method should process only submission from ``submissions``.
        """
        if not (self.is_user_disqualified(request, user) or (is_contest_admin(request) and self.user_has_disqualification_history(request, user))):
            return None

        disqualified_submissions = []
        for submission in submissions:
            if self.is_submission_disqualified(submission) or (is_contest_admin(request) and self.has_disqualification_history(submission)):
                disqualified_submissions.append(
                    {
                        "submission": submission,
                        "reason": self._render_disqualification_reason(request, submission),
                    }
                )

        contestwide = self._render_contestwide_disqualification_reason(request, user)
        if not disqualified_submissions and not contestwide:
            return None

        if is_contest_admin(request):
            template = "disqualification/submissions-admin.html"
        else:
            template = "disqualification/submissions.html"

        return render_to_string(
            template,
            request=request,
            context={
                "submissions": disqualified_submissions,
                "contestwide": contestwide,
                "contest_disq_info": self._get_contest_disq_info(),
            },
        )

    def get_contest_participant_info_list(self, request, user):
        submissions = Submission.objects.filter(problem_instance__contest=request.contest, user=user).order_by("-date").select_related()

        info_list = super(DisqualificationContestControllerMixin, self).get_contest_participant_info_list(request, user)

        disqualification = self.render_disqualifications(request, user, submissions)
        if disqualification:
            info_list.append((75, disqualification))
        return info_list


ContestController.mix_in(DisqualificationContestControllerMixin)


class DisqualificationProgrammingContestControllerMixin:
    """ContestController mixin that renders submission disqualification info."""

    def render_submission(self, request, submission):
        prev = super(DisqualificationProgrammingContestControllerMixin, self).render_submission(request, submission)

        if self.is_submission_disqualified(submission) or (is_contest_admin(request) and self.has_disqualification_history(submission)):
            return prev + self.render_submission_disqualifiaction(request, submission)
        return prev


ProgrammingContestController.mix_in(DisqualificationProgrammingContestControllerMixin)


class WithDisqualificationRankingControllerMixin:
    """RankingController mixin that manages disqualification module influence
    on rankings.
    """

    def _show_disqualified(self, key):
        """Decides if disqualified users should be included in the ranking.

        They will be marked as disqualified and will *not* influence the
        places of other contestants.
        """
        return self.is_admin_key(key)

    def filter_users_for_ranking(self, key, queryset):
        qs = super(WithDisqualificationRankingControllerMixin, self).filter_users_for_ranking(key, queryset)

        if not self._show_disqualified(key):
            qs = self.contest.controller.exclude_disqualified_users(qs)

        return qs

    def _render_ranking_page(self, key, data, page):
        if not self._show_disqualified(key):
            return super(WithDisqualificationRankingControllerMixin, self)._render_ranking_page(key, data, page)

        request = self._fake_request(page)
        data["is_admin"] = self.is_admin_key(key)
        return render_to_string("disqualification/default-ranking.html", context=data, request=request)

    def _get_csv_header(self, key, data):
        header = super(WithDisqualificationRankingControllerMixin, self)._get_csv_header(key, data)
        if self._show_disqualified(key):
            header.append(_("Disqualified"))
        return header

    def _get_csv_row(self, key, row):
        line = super(WithDisqualificationRankingControllerMixin, self)._get_csv_row(key, row)
        if self._show_disqualified(key):
            line.append(_("Yes") if row.get("disqualified") else _("No"))
        return line

    def serialize_ranking(self, key):
        data = super(WithDisqualificationRankingControllerMixin, self).serialize_ranking(key)
        if not self._show_disqualified(key):
            return data
        return self._annotate_disqualified(key, data)

    def _annotate_disqualified(self, key, data):
        users_ids = [row["user"].id for row in data["rows"]]
        not_disqualified = self.contest.controller.exclude_disqualified_users(User.objects.filter(id__in=users_ids))

        for row in data["rows"]:
            row["disqualified"] = row["user"] not in not_disqualified
        return data

    def _ignore_in_ranking_places(self, data_row):
        prev = super(WithDisqualificationRankingControllerMixin, self)._ignore_in_ranking_places(data_row)
        return prev or data_row.get("disqualified", False)


DefaultRankingController.mix_in(WithDisqualificationRankingControllerMixin)
