from django.template.loader import render_to_string
from django.utils.safestring import mark_safe
from django.contrib.auth.models import User
from django.template.context import RequestContext
from django.utils.translation import ugettext_lazy as _

from oioioi.contests.utils import is_contest_admin, is_contest_observer
from oioioi.disqualification.models import Disqualification
from oioioi.programs.controllers import ProgrammingContestController
from oioioi.contests.controllers import submission_template_context, \
    ContestController
from oioioi.rankings.controllers import DefaultRankingController

import oioioi.disqualification.views  # pylint: disable=unused-import


class DisqualificationContestControllerMixin(object):
    def is_submission_disqualified(self, submission):
        """Decides whether the submission is currently disqualified.

           This won't automatically propagate to user disqualification.
           Used mostly with single submission context.
        """
        return Disqualification.objects.filter(submission=submission,
                guilty=True).exists()

    def has_disqualification_history(self, submission):
        """Should be ``True`` if the submission was disqualified anytime.

           This method is for example used to check if the disqualification
           admin panel should be displayed.
        """
        return Disqualification.objects.filter(submission=submission).exists()

    def is_any_submission_to_problem_disqualified(self,
            user, problem_instance):
        """Should be ``True`` if the given user has any disqualified
           submission to this problem.

           If so, this will usually result in hiding scores in other
           submissions to this problem.
        """
        return Disqualification.objects.filter(
                user=user,
                submission__problem_instance=problem_instance, guilty=True) \
            .exists()

    def is_user_disqualified(self, request, user):
        """True if the user should be considered disqualified

           The default implementation *does not* infer it from
           previous methods.
        """
        return Disqualification.objects.filter(contest=request.contest,
            user=user, guilty=True).exists()

    def exclude_disqualified_users(self, request, queryset):
        """Filters the queryset of :class:`~django.contrib.auth.model.User`
           to select only users which are not disqualified in this contest.
        """
        return queryset.exclude(
                disqualification__in=Disqualification.objects.filter(
                        contest=request.contest, guilty=True))

    def results_visible(self, request, submission):
        normally = super(DisqualificationContestControllerMixin, self) \
            .results_visible(request, submission)

        if is_contest_admin(request) or is_contest_observer(request):
            return normally

        return normally and \
                not self.is_any_submission_to_problem_disqualified(
                    submission.user, submission.problem_instance)

    def change_submission_kind(self, submission, kind):
        """Changing the kind of submission should undisqualify given submission
        """
        old_kind = submission.kind
        super(DisqualificationContestControllerMixin, self) \
            .change_submission_kind(submission, kind)

        if submission.kind != old_kind:
            Disqualification.objects.filter(submission=submission).update(
                guilty=False)

    def _render_disqualification_reason(self, request, submission):
        """Renders part with reason of the given submission disqualification.

           This method is only used internally.
        """
        reasons = Disqualification.objects.filter(submission=submission)
        if not is_contest_admin(request):
            reasons = reasons.filter(guilty=True)

        if not reasons:
            return mark_safe("")
        return render_to_string('disqualification/custom.html',
            context_instance=RequestContext(request, {
                'submission': submission_template_context(request,
                    submission.programsubmission),
                'reasons': reasons,
            }))

    def render_submission_disqualifiaction(self, request, submission):
        """Renders the disqualification reason of the given submission to HTML.
        """
        reason = self._render_disqualification_reason(request, submission)
        template = 'disqualification/generic.html'

        if is_contest_admin(request):
            template = 'disqualification/generic_admin.html'

        return render_to_string(template,
            context_instance=RequestContext(request, {
                'submission': submission_template_context(request,
                    submission.programsubmission),
                'reason': reason,
            }))

    def _render_contestwide_disqualification_reason(self, request):
        """Renders part with reason of the current user disqualification not
           directly associated with any particular submission.

           This method is only used internally.
        """
        reasons = Disqualification.objects.filter(user=request.user,
                contest=request.contest, submission__isnull=True)
        if not is_contest_admin(request):
            reasons = reasons.filter(guilty=True)

        if not reasons:
            return None
        return render_to_string('disqualification/custom.html',
            context_instance=RequestContext(request, {
                'reasons': reasons,
            }))

    def render_my_submissions_header(self, request, submissions):
        header = super(DisqualificationContestControllerMixin, self) \
                .render_my_submissions_header(request, submissions)
        disq_header = self.render_disqualifications(request, submissions)
        if disq_header:
            header += disq_header
        return header

    def render_disqualifications(self, request, submissions):
        """Renders all disqualifications of the current user to HTML, which
           may be put anywhere on the site.

           This method should process only submission from ``submissions``.
        """
        if not self.is_user_disqualified(request, request.user):
            return None

        disqualified_submissions = []
        for submission in submissions:
            if self.is_submission_disqualified(submission):
                disqualified_submissions.append({
                    'submission': submission,
                    'reason': self._render_disqualification_reason(
                            request, submission)
                })

        contestwide = self._render_contestwide_disqualification_reason(request)
        if not disqualified_submissions and not contestwide:
            return None

        return render_to_string('disqualification/my_submissions.html',
            context_instance=RequestContext(request, {
                'submissions': disqualified_submissions,
                'contestwide': contestwide,
            }))


ContestController.mix_in(DisqualificationContestControllerMixin)


class DisqualificationProgrammingContestControllerMixin(object):
    def render_submission(self, request, submission):
        prev = super(DisqualificationProgrammingContestControllerMixin, self) \
            .render_submission(request, submission)

        if self.is_submission_disqualified(submission) or \
                (is_contest_admin(request) and
                    self.has_disqualification_history(submission)):
            return prev + self.render_submission_disqualifiaction(request,
                submission)
        return prev


ProgrammingContestController.mix_in(
    DisqualificationProgrammingContestControllerMixin)


class WithDisqualificationRankingControllerMixin(object):
    def _show_disqualified(self, request):
        """Decides if disqualified users should be included in the ranking.

           They will be marked as disqualified and will *not* influence the
           places of other contestants.
        """
        return is_contest_admin(request)

    def filter_users_for_ranking(self, request, key, queryset):
        qs = super(WithDisqualificationRankingControllerMixin, self) \
            .filter_users_for_ranking(request, key, queryset)

        if not self._show_disqualified(request):
            qs = request.contest.controller.exclude_disqualified_users(
                    request, qs)

        return qs

    def render_ranking(self, request, key):
        if not self._show_disqualified(request):
            return super(WithDisqualificationRankingControllerMixin, self) \
                .render_ranking(request, key)

        data = self.serialize_ranking(request, key)
        return render_to_string('disqualification/default_ranking.html',
            context_instance=RequestContext(request, data))

    def _get_csv_header(self, request, data):
        header = super(WithDisqualificationRankingControllerMixin, self) \
            ._get_csv_header(request, data)
        if self._show_disqualified(request):
            header.append(_("Disqualified"))
        return header

    def _get_csv_row(self, request, row):
        line = super(WithDisqualificationRankingControllerMixin, self) \
            ._get_csv_row(request, row)
        if self._show_disqualified(request):
            line.append(_("Yes") if row.get('disqualified') else _("No"))
        return line

    def serialize_ranking(self, request, key):
        data = super(WithDisqualificationRankingControllerMixin, self) \
            .serialize_ranking(request, key)
        if not self._show_disqualified(request):
            return data
        return self._annotate_disqualified(request, key, data)

    def _annotate_disqualified(self, request, key, data):
        users_ids = [row['user'].id for row in data['rows']]
        not_disqualified = request.contest.controller \
            .exclude_disqualified_users(request,
                                        User.objects.filter(id__in=users_ids))

        for row in data['rows']:
            row['disqualified'] = row['user'] not in not_disqualified
        return data

    def _ignore_in_ranking_places(self, data_row):
        prev = super(WithDisqualificationRankingControllerMixin, self) \
                ._ignore_in_ranking_places(data_row)
        return prev or data_row.get('disqualified', False)


DefaultRankingController.mix_in(WithDisqualificationRankingControllerMixin)
