from datetime import timedelta
import json
import logging
import pprint

from django.db import transaction
from django.template import RequestContext
from django.template.loader import render_to_string
from django.core.exceptions import PermissionDenied, ObjectDoesNotExist
from django.core.urlresolvers import reverse
from django.conf import settings
from django.utils import timezone
from django.utils.translation import ugettext_noop, ugettext_lazy as _
from django.utils.safestring import mark_safe
from django.contrib.auth.models import User
from django.core.mail import EmailMessage

from oioioi.base.utils import RegisteredSubclassesBase, ObjectWithMixins, \
        get_user_display_name
from oioioi.contests.models import Submission, Round, UserResultForRound, \
        UserResultForProblem, FailureReport, SubmissionReport, \
        UserResultForContest, submission_kinds, ProblemStatementConfig, \
        RoundTimeExtension
from oioioi.contests.scores import ScoreValue
from oioioi.contests.utils import visible_problem_instances, rounds_times, \
        is_contest_admin, is_contest_observer, last_break_between_rounds, \
        has_any_active_round
from oioioi.problems.controllers import ProblemController
from oioioi import evalmgr


logger = logging.getLogger(__name__)


def export_entries(registry, values):
    result = []
    for value, description in registry.entries:
        if value in values:
            result.append((value, description))
    return result


def submission_template_context(request, submission):
    pi = submission.problem_instance
    controller = pi.controller
    can_see_status = controller.can_see_submission_status(request, submission)
    can_see_score = controller.can_see_submission_score(request, submission)
    can_see_comment = controller.can_see_submission_comment(request,
            submission)
    link = reverse('submission', kwargs={
        'submission_id': submission.id,
        'contest_id': pi.contest.id if pi.contest else None})

    valid_kinds = controller.valid_kinds_for_submission(submission)
    valid_kinds.remove(submission.kind)
    valid_kinds_for_submission = export_entries(submission_kinds,
            valid_kinds)

    return {'submission': submission,
            'can_see_status': can_see_status,
            'can_see_score': can_see_score,
            'can_see_comment': can_see_comment,
            'link': link,
            'valid_kinds_for_submission': valid_kinds_for_submission}


class RegistrationController(RegisteredSubclassesBase, ObjectWithMixins):
    def __init__(self, contest):
        self.contest = contest

    def can_enter_contest(self, request):
        """Determines if the current user is allowed to enter the contest,
           i.e. see any page related to the contest.

           The default implementation uses :meth:`filter_participants` on
           a single-row queryset for non-anonymous users. For anonymous,
           :meth:`anonymous_can_enter_contest` is called.

           Contest administrators are also allowed, regardless of what
           :meth:`filter_participants` returns.

           :rtype: bool
        """
        if request.user.is_anonymous():
            return self.anonymous_can_enter_contest()
        if request.user.has_perm('contests.contest_admin', self.contest):
            return True
        if request.user.has_perm('contests.contest_observer', self.contest):
            return True
        if request.user.has_perm('contests.personal_data', self.contest):
            return True
        queryset = User.objects.filter(id=request.user.id)
        return bool(self.filter_participants(queryset))

    def anonymous_can_enter_contest(self):
        """Determines if an anonymous user can enter the contest.

           Allowed anonymous users will have limited functionality, but they
           can see the problems, review questions etc. Modules should give them
           as much functionality as reasonably possible.

           :rtype: bool
        """
        raise NotImplementedError

    def filter_participants(self, queryset):
        """Filters the queryset of :class:`~django.contrib.auth.model.User`
           to select only users which have access to the contest.
        """
        raise NotImplementedError

    def no_entry_view(self, request):
        """View rendered when a user would like to perform an action not
           allowed by this registration controller.

           This may be a good place to put a redirection to a registration page
           etc.

           The default implementation just raises ``PermissionDenied``.
        """
        raise PermissionDenied

    def mixins_for_admin(self):
        """Returns an iterable of mixins to add to the default
           :class:`oioioi.contests.admin.ContestAdmin` for
           the contest.

           The default implementation returns an empty tuple.
        """
        return ()

    def get_contest_participant_info_list(self, request, user):
        """Returns a list of tuples (priority, info).
           Each entry represents a fragment of HTML with information about the
           user's participation in the contest. This information will be
           visible for contest admins. It can be any information an application
           wants to add.

           The fragments are sorted by priority (descending) and rendered in
           that order.

           The default implementation returns basic info about the contestant:
           his/her full name, e-mail, the user id, his/her submissions and
           round time extensions.

           To add additional info from another application, override this
           method. For integrity, include the result of the parent
           implementation in your output.
        """
        return []

    def filter_users_with_accessible_personal_data(self, queryset):
        """Filters the queryset of :class:`~django.contrib.auth.model.User`
           to select only users whose personal data is accessible to the
           admins.
        """
        raise NotImplementedError


class PublicContestRegistrationController(RegistrationController):
    description = _("Public contest")

    def can_enter_contest(self, request):
        return True

    def anonymous_can_enter_contest(self):
        return True

    def filter_participants(self, queryset):
        return queryset

    def filter_users_with_accessible_personal_data(self, queryset):
        submissions = Submission.objects.filter(
                problem_instance__contest=self.contest)
        authors = [s.user for s in submissions]
        return [q for q in queryset if q in authors]


class ContestController(RegisteredSubclassesBase, ObjectWithMixins):
    """Contains the contest logic and rules.

       This is the computerized implementation of the contest's official
       rules.
    """

    modules_with_subclasses = ['controllers']
    abstract = True

    def __init__(self, contest):
        self.contest = contest

    def registration_controller(self):
        return PublicContestRegistrationController(self.contest)

    def default_view(self, request):
        """Determines the default landing page for the user from the passed
           request.

           The default implementation returns the list of problems.
        """
        return reverse('problems_list', kwargs={'contest_id': self.contest.id})

    def get_contest_participant_info_list(self, request, user):
        """Returns a list of tuples (priority, info).
           Each entry represents a fragment of HTML with information about the
           user's participation in the contest. This information will be
           visible for contest admins. It can be any information an application
           wants to add.

           The fragments are sorted by priority (descending) and rendered in
           that order.

           The default implementation returns basic info about the contestant:
           his/her full name, e-mail, the user id, his/her submissions and
           round time extensions.

           To add additional info from another application, override this
           method. For integrity, include the result of the parent
           implementation in your output.
        """
        res = [(100, render_to_string('contests/basic_user_info.html', {
                        'request': request,
                        'target_user_name': self.get_user_public_name(request,
                                                                      user),
                        'target_user': user,
                        'user': request.user}))]

        exts = RoundTimeExtension.objects.filter(user=user,
                round__contest=request.contest)
        if exts.exists():
            res.append((99,
                    render_to_string('contests/roundtimeextension_info.html', {
                            'request': request,
                            'extensions': exts,
                            'user': request.user})))

        if is_contest_admin(request) or is_contest_observer(request):
            submissions = Submission.objects.filter(
                    problem_instance__contest=request.contest, user=user) \
                    .order_by('-date').select_related()

            if submissions.exists():
                submission_records = [submission_template_context(request, s)
                        for s in submissions]
                context = {
                    'submissions': submission_records,
                    'show_scores': True
                }
                rendered_submissions = render_to_string(
                        'contests/user_submissions_table.html',
                        context_instance=RequestContext(request, context))
                res.append((50, rendered_submissions))

        return res

    def get_user_public_name(self, request, user):
        """Returns the name of the user to be displayed in public contest
           views.

           The default implementation returns the user's full name or username
           if the former is not available.
        """
        return get_user_display_name(user)

    def get_round_times(self, request, round):
        """Determines the times of the round for the user doing the request.

           The default implementation returns an instance of
           :class:`RoundTimes` cached by round_times() method.

           Round must belong to request.contest.

           :returns: an instance of :class:`RoundTimes`
        """
        return rounds_times(request)[round]

    def separate_public_results(self):
        """Determines if there should be two separate dates for personal
           results (when participants can see their scores for a given round)
           and public results (when round ranking is published).

           Depending on the value returned, contest admins can see and modify
           both ``Results date`` and ``Public results date`` or only the
           first one.

           :rtype: bool
        """
        return False

    def order_rounds_by_focus(self, request, queryset=None):
        """Sorts the rounds in the queryset according to probable user's
           interest.

           The algorithm works as follows (roughly):

               1. If a round starts or ends in 10 minutes or less
                  or started less than a minute ago, it's prioritized.
               1. Then active rounds are appended.
               1. If a round starts in less than 6 hours or has ended in less
                  than 1 hour, it's appended.
               1. Then come past rounds.
               1. Then other future rounds.

           See the implementation for corner cases.

           :param request: the Django request
           :param queryset: the set of :class:`~oioioi.contests.models.Round`
             instances to sort or ``None`` to return all rounds of the
             controller's contest
        """

        if queryset is None:
            queryset = Round.objects.filter(contest=self.contest)
        now = request.timestamp

        def sort_key(round):
            rtimes = self.get_round_times(request, round)
            to_event = timedelta(minutes=10)
            focus_after_start = timedelta(minutes=1)
            if rtimes.get_start() and now >= rtimes.get_start() \
                    and now <= rtimes.get_start() + focus_after_start:
                to_event = now - rtimes.get_start()
            if rtimes.is_future(now):
                to_event = min(to_event, rtimes.get_start() - now)
            elif rtimes.is_active(now):
                to_event = min(to_event, rtimes.get_end() - now)

            to_event_inactive = timedelta(hours=6)
            focus_after_end = timedelta(hours=1)
            if rtimes.get_end() and now >= rtimes.get_end() \
                    and now <= rtimes.get_end() + focus_after_end:
                to_event_inactive = now - rtimes.get_end()
            if rtimes.is_future(now):
                to_event_inactive = min(to_event_inactive,
                                        rtimes.get_start() - now)
            return (to_event, not rtimes.is_active(now),
                    to_event_inactive, bool(now < rtimes.get_start()),
                    abs(rtimes.get_start() - now))
        return sorted(queryset, key=sort_key)

    def can_see_round(self, request, round):
        """Determines if the current user is allowed to see the given round.

           If not, everything connected with this round will be hidden.

           The default implementation checks if the round is not in the future.
        """
        if is_contest_admin(request):
            return True
        rtimes = self.get_round_times(request, round)
        return not rtimes.is_future(request.timestamp)

    def can_see_ranking(self, request):
        """Determines if the current user is allowed to see the ranking.

           The default implementation allows it to everyone.
         """
        return True

    def can_see_problem(self, request, problem_instance):
        """Determines if the current user is allowed to see the given problem.

           If not, the problem will be hidden from all lists, so that its name
           should not be visible either.

           The default implementation checks if the user can see the given
           round (calls :meth:`can_see_round`).
        """
        if not problem_instance.round:
            return False
        if is_contest_admin(request):
            return True
        return self.can_see_round(request, problem_instance.round)

    def can_see_statement(self, request, problem_instance):
        """Determines if the current user is allowed to see the statement for
           the given problem.

           The default implementation checks if there exists a problem
           statement config for current contest and checks if statements'
           visibility is enabled. If there is no problem statement config for
           current contest or option 'AUTO' is chosen, returns default value
           (calls :meth:`default_can_see_statement`)
        """
        if is_contest_admin(request):
            return True
        psc = ProblemStatementConfig.objects.filter(contest=request.contest)
        if psc.exists() and psc[0].visible != 'AUTO':
            return psc[0].visible == 'YES'
        else:
            return self.default_can_see_statement(request, problem_instance)

    def default_can_see_statement(self, request, problem_instance):
        return True

    def can_submit(self, request, problem_instance, check_round_times=True):
        """Determines if the current user is allowed to submit a solution for
           the given problem.

           The default implementation checks if the user is not anonymous,
           and if the round is active for the given user. Subclasses should
           also call this default implementation.
        """
        if request.user.is_anonymous():
            return False
        if not problem_instance.round:
            return False
        if is_contest_admin(request):
            return True

        if check_round_times:
            rtimes = self.get_round_times(request, problem_instance.round)
            return rtimes.is_active(request.timestamp)
        else:
            return True

    def get_default_submission_kind(self, request, **kwargs):
        """Returns default kind of newly created submission by the current
           user.

           The default implementation returns ``'IGNORED'`` for
           non-contestants.  In other cases it returns ``'NORMAL'``.
        """
        if is_contest_admin(request) or is_contest_observer(request):
            return 'IGNORED'
        return 'NORMAL'

    def get_submissions_limit(self, request, problem_instance):
        if is_contest_admin(request):
            return None
        return problem_instance.submissions_limit

    def adjust_submission_form(self, request, form, problem_instance):
        pass

    def validate_submission_form(self, request, problem_instance, form,
            cleaned_data):
        return cleaned_data

    def create_submission(self, request, problem_instance, form_data,
                          **kwargs):
        raise NotImplementedError

    def judge(self, submission, extra_args=None, is_rejudge=False):
        submission.problem_instance.problem.controller \
            .judge(submission, extra_args, is_rejudge)

    def fill_evaluation_environ(self, environ, submission):
        pass

    def get_supported_extra_args(self, submission):
        """Returns dict of all values which can be provided in extra_args
           argument to the judge method.
        """
        problem = submission.problem_instance.problem
        return problem.controller.get_supported_extra_args(submission)

    def finalize_evaluation_environment(self, environ):
        """This method gets called right before the environ becomes scheduled
           in the queue.

           This hook exists for inserting extra handlers to the recipe before
           judging the solution.
        """
        pass

    def submission_queued(self, submission, async_result):
        """This method gets called right after the submission becomes scheduled
           in the queue with async_result from delay.
        """
        pass

    def submission_unqueued(self, submission, job_id):
        """This method gets called right after the submission had been judged
           and is about to leave the assigned workers.

           This hook gets called AFTER submission_judged.
        """
        pass

    def submission_judged(self, submission, rejudged=False):
        if submission.user is not None and not rejudged:
            logger.info("Submission %(submission_id)d by user %(username)s"
                        " for problem %(short_name)s was judged",
                        {'submission_id': submission.pk,
                         'username': submission.user.username,
                         'short_name': submission.problem_instance.short_name},
                            extra={'notification': 'submission_judged',
                                   'user': submission.user,
                                   'submission': submission})

    def _activate_newest_report(self, submission, queryset, kind=None):
        problem = submission.problem_instance.problem
        problem.controller._activate_newest_report(submission, queryset, kind)

    def update_report_statuses(self, submission, queryset):
        problem = submission.problem_instance.problem
        problem.controller.update_report_statuses(submission, queryset)

    def update_submission_score(self, submission):
        """Updates status, score and comment in a submission.

           Usually this involves looking at active reports and aggregating
           information from them.
        """
        raise NotImplementedError

    def update_user_result_for_problem(self, result):
        problem = result.problem_instance.problem
        problem.controller.update_user_result_for_problem(result)

    def _sum_scores(self, scores):
        scores = [s for s in scores if s is not None]
        return scores and sum(scores[1:], scores[0]) or None

    def update_user_result_for_round(self, result):
        """Updates a :class:`~oioioi.contests.models.UserResultForRound`.

           Usually this involves looking at user's results for problems and
           aggregating scores from them. Default implementation sums the
           scores.

           Saving the ``result`` is a responsibility of the caller.
        """
        scores = UserResultForProblem.objects \
                .filter(user=result.user) \
                .filter(problem_instance__round=result.round) \
                .values_list('score', flat=True)
        result.score = self._sum_scores(map(ScoreValue.deserialize, scores))

    def update_user_result_for_contest(self, result):
        """Updates a :class:`~oioioi.contests.models.UserResultForContest`.

           Usually this involves looking at user's results for rounds and
           aggregating scores from them. Default implementation sums the
           scores.

           Saving the ``result`` is a responsibility of the caller.
        """
        scores = UserResultForRound.objects \
                .filter(user=result.user) \
                .filter(round__contest=result.contest) \
                .filter(round__is_trial=False) \
                .values_list('score', flat=True)
        result.score = self._sum_scores(map(ScoreValue.deserialize, scores))

    def update_user_results(self, user, problem_instance):
        """Updates score for problem instance, round and contest.

           Usually this method creates instances (if they don't exist) of:
           * :class:`~oioioi.contests.models.UserResultForProblem`
           * :class:`~oioioi.contests.models.UserResultForRound`
           * :class:`~oioioi.contests.models.UserResultForContest`

           and then calls proper methods of ContestController to update them.
        """
        round = problem_instance.round
        contest = round.contest
        problem = problem_instance.problem

        # We do this in three separate transactions, because in some database
        # engines (namely MySQL in REPEATABLE READ transaction isolation level)
        # data changed by a transaction is not visible in subsequent SELECTs
        # even in the same transaction.

        # First: UserResultForProblem

        problem.controller.update_user_results(user, problem_instance)

        # Second: UserResultForRound
        with transaction.atomic():
            result, created = UserResultForRound.objects.select_for_update() \
                .get_or_create(user=user, round=round)
            self.update_user_result_for_round(result)
            result.save()

        # Third: UserResultForContest
        with transaction.atomic():
            result, created = UserResultForContest.objects \
                    .select_for_update() \
                    .get_or_create(user=user, contest=contest)
            self.update_user_result_for_contest(result)
            result.save()

    def filter_my_visible_submissions(self, request, queryset):
        """Returns the submissions which the user should see in the
           "My submissions" view.

           The default implementation returns all submissions belonging to
           the user for the problems that are visible, except for admins, which
           get all their submissions.

           Should return the updated queryset.
        """
        if not request.user.is_authenticated():
            return queryset.none()
        qs = queryset.filter(user=request.user)
        if is_contest_admin(request):
            return qs
        else:
            return qs.filter(date__lte=request.timestamp) \
            .filter(problem_instance__in=visible_problem_instances(request)) \
            .exclude(kind='IGNORED_HIDDEN')

    def results_visible(self, request, submission):
        """Determines whether it is a good time to show the submission's
           results.

           This method is not used directly in any code outside of the
           controllers. It's a helper method used in a number of other
           controller methods, as described.

           The default implementations uses the round's
           :attr:`~oioioi.contests.models.Round.results_date`. If it's
           ``None``, results are not available. Admins are always shown the
           results.
        """
        if is_contest_admin(request) or is_contest_observer(request):
            return True
        round = submission.problem_instance.round
        rtimes = self.get_round_times(request, round)
        return rtimes.results_visible(request.timestamp)

    def filter_visible_reports(self, request, submission, queryset):
        """Determines which reports the user should be able to see.

           It need not check whether the submission is visible to the user.

           The default implementation uses
           :meth:`~ContestController.results_visible`.

           :param request: Django request
           :param submission: instance of
                              :class:`~oioioi.contests.models.Submission`
           :param queryset: a queryset, initially filtered at least to
                              select only given submission's reports
           :returns: updated queryset
        """
        if is_contest_admin(request) or is_contest_observer(request):
            return queryset
        if self.results_visible(request, submission):
            return queryset.filter(status='ACTIVE', kind='NORMAL')
        return queryset.none()

    def can_see_submission_status(self, request, submission):
        return submission.problem_instance.problem.controller \
            .can_see_submission_status(request, submission)

    def can_see_submission_score(self, request, submission):
        return submission.problem_instance.problem.controller \
            .can_see_submission_score(request, submission)

    def can_see_submission_comment(self, request, submission):
        return submission.problem_instance.problem.controller \
            .can_see_submission_comment(request, submission)

    def render_submission_date(self, submission):
        problem = submission.problem_instance.problem
        return problem.controller.render_submission_date(submission)

    def render_submission_score(self, submission):
        problem = submission.problem_instance.problem
        return problem.controller.render_submission_score(submission)

    def render_submission(self, request, submission):
        """Renders the given submission to HTML.

           This is usually a table with some basic submission info,
           source code download etc., displayed on the top of the
           submission details view, above the reports.
        """
        raise NotImplementedError

    def render_submission_footer(self, request, submission):
        return submission.problem.controller \
                .render_submission_footer(request, submission)

    def render_report(self, request, report):
        problem = report.submission.problem_instance.problem
        return ProblemController.render_report(problem.controller, request,
                                               report)

    def render_my_submissions_header(self, request, submissions):
        """Renders header on "My submissions" view.

           Default implementation returns empty string.
        """
        return mark_safe("")

    def adjust_contest(self):
        """Called when a (usually new) contest has just got the controller
           attached or after the contest has been modified."""
        pass

    def valid_kinds_for_submission(self, submission):
        return submission.problem.controller \
                .valid_kinds_for_submission(submission)

    def change_submission_kind(self, submission, kind):
        return submission.problem.controller \
            .change_submission_kind(submission, kind)

    def mixins_for_admin(self):
        """Returns an iterable of mixins to add to the default
           :class:`oioioi.contests.admin.ContestAdmin` for
           this particular contest.

           The default implementation returns an empty tuple.
        """
        return ()

    def is_onsite(self):
        """Determines whether the contest is on-site."""
        return False

    def send_email(self, subject, body, recipients, headers=None):
        """Send an email about something related to this contest
            (e.g. a submission confirmation).
            ``From:`` is set to DEFAULT_FROM_EMAIL,
            ``Reply-To:`` is taken from the ``Contact email`` contest setting
                and defaults to the value of ``From:``.
        """
        replyto = settings.DEFAULT_FROM_EMAIL
        if self.contest.contact_email:
            replyto = self.contest.contact_email

        final_headers = {'Reply-To': replyto}
        if headers:
            final_headers.update(headers)
        email = EmailMessage(subject, body, settings.DEFAULT_FROM_EMAIL,
                recipients, headers=final_headers)
        email.send()

    def _is_partial_score(self, test_report):
        if not test_report:
            return False
        return test_report.submission_report.submission.problem \
                .controller._is_partial_score(test_report)



class PastRoundsHiddenContestControllerMixin(object):
    """ContestController mixin that hides past rounds
       if another round is starting soon.

       The period when the past rounds are hidden is called
       round's *preparation time*.

       Do not use it with overlapping rounds.
    """

    def can_see_round(self, request, round):
        """Decides whether the given round should be shown for the given user.
           The algorithm is as follows:

                1. Round is always visible for contest admins.
                1. If any round is active, all active rounds are visible,
                   all other rounds are hidden.
                1. Let
                       break_start = latest end_date of any past round
                       break_end = closest start_date of any future round
                       break_time = break_end - break_start

                    then preparation_time is the last 30 minutes of the break,
                    or if the break is shorter then just its second half.

                1. During the preparation_time all rounds should be hidden.
                1. Otherwise the decision is made by the superclass method.
        """

        if is_contest_admin(request):
            return True

        rtimes = self.get_round_times(request, round)
        if has_any_active_round(request):
            return rtimes.is_active(request.timestamp)

        left, right = last_break_between_rounds(request)
        if left is not None and right is not None:
            last_break_time = right - left
            preparation_start = right - min(
                    timedelta(minutes=30),
                    last_break_time // 2
            )
            preparation_end = right
            if preparation_start < request.timestamp < preparation_end:
                return False

        return super(PastRoundsHiddenContestControllerMixin, self) \
                .can_see_round(request, round)


class NotificationsMixinForContestController(object):

    def users_to_receive_public_message_notification(self):
        """Decide if all users particiapting in a contest should be
           notified about a new global message.

           This should be disabled for contest with many users
           because of performance reasons - for each user, a single
           query to database is executed while sending a notification.
        """
        return []

    def get_notification_message_submission_judged(self, submission):
        """Return a message to show in a notification when a
           submission has been judged.
        """
        return ugettext_noop("Your submission was judged.")

ContestController.mix_in(NotificationsMixinForContestController)


class ProblemUploadingContestControllerMixin(object):
    def adjust_upload_form(self, request, existing_problem, form):
        """Adjusts the problem upload form created by some sublcass of
           :class:`~oioioi.problems.problem_sources.PackageSource`.

           Called from
           :meth:`~oioioi.problems.problem_sources.PackageSource.view`.
        """
        pass

    def fill_upload_environ(self, request, form, env):
        """Extends the `env` dictionary used during problem uploading.

           Called from
           :meth:`~oioioi.problems.problem_sources.PackageSource.view`.
        """
        pass
ContestController.mix_in(ProblemUploadingContestControllerMixin)
