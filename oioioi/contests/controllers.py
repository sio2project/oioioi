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
from django.utils.translation import ugettext_lazy as _
from django.utils.safestring import mark_safe
from django.contrib.auth.models import User

from oioioi.base.utils import RegisteredSubclassesBase, ObjectWithMixins
from oioioi.contests.models import Submission, Round, UserResultForRound, \
        UserResultForProblem, FailureReport, SubmissionReport, \
        UserResultForContest, submission_kinds
from oioioi.contests.scores import ScoreValue
from oioioi.contests.utils import visible_problem_instances, rounds_times, \
        is_contest_admin, is_contest_observer
from oioioi import evalmgr


logger = logging.getLogger(__name__)


def export_entries(registry, values):
    result = []
    for value, description in registry.entries:
        if value in values:
            result.append((value, description))
    return result


def submission_template_context(request, submission):
    controller = submission.problem_instance.contest.controller
    can_see_status = controller.can_see_submission_status(request, submission)
    can_see_score = controller.can_see_submission_score(request, submission)
    can_see_comment = controller.can_see_submission_comment(request,
            submission)

    valid_kinds = controller.valid_kinds_for_submission(submission)
    valid_kinds.remove(submission.kind)
    valid_kinds_for_submission = export_entries(submission_kinds,
            valid_kinds)

    return {'submission': submission,
            'can_see_status': can_see_status,
            'can_see_score': can_see_score,
            'can_see_comment': can_see_comment,
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


class PublicContestRegistrationController(RegistrationController):
    description = _("Public contest")

    def can_enter_contest(self, request):
        return True

    def anonymous_can_enter_contest(self):
        return True

    def filter_participants(self, queryset):
        return queryset


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

    def get_round_times(self, request, round):
        """Determines the times of the round for the user doing the request.

           The default implementation returns an instance of :class:`RoundTimes`
           cached by round_times() method.

           Round must belong to request.contest.

           :returns: an instance of :class:`RoundTimes`
        """
        return rounds_times(request)[round]

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
           :patam queryset: the set of :class:`~oioioi.contests.models.Round`
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

           The default implementation checks round dates.
        """
        if is_contest_admin(request):
            return True
        rtimes = self.get_round_times(request, round)
        return not rtimes.is_future(request.timestamp)

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

    def get_default_submission_kind(self, request):
        """Returns default kind of newly created submission by the current user.

           The default implementation returns ``'IGNORED'`` for non-contestants.
           In other cases it returns ``'NORMAL'``.
        """
        if is_contest_admin(request) or is_contest_observer(request):
            return 'IGNORED'
        return 'NORMAL'

    def get_submissions_limit(self, request, problem_instance):
        if is_contest_admin(request):
            return None
        return problem_instance.submissions_limit

    def is_submissions_limit_exceeded(self, request, problem_instance, kind):
        submissions_number = Submission.objects.filter(user=request.user,
            problem_instance__id=problem_instance.id, kind=kind).count()
        submissions_limit = self.get_submissions_limit(request,
            problem_instance)
        if submissions_limit and submissions_number >= submissions_limit:
            return True
        return False

    def adjust_submission_form(self, request, form):
        pass

    def validate_submission_form(self, request, problem_instance, form,
            cleaned_data):
        return cleaned_data

    def create_submission(self, request, problem_instance, form_data, **kwargs):
        raise NotImplementedError

    def fill_evaluation_environ(self, environ, submission):
        problem_instance = submission.problem_instance
        problem = problem_instance.problem
        round = problem_instance.round
        assert round, \
            "Someone tried to evaluate submission to dangling problem instance."
        contest = round.contest

        environ['submission_id'] = submission.id
        environ['submission_kind'] = submission.kind
        environ['problem_instance_id'] = problem_instance.id
        environ['problem_id'] = problem.id
        environ['round_id'] = round.id
        environ['contest_id'] = contest.id

        environ['report_kinds'] = ['INITIAL', 'NORMAL']
        if 'hidden_judge' in environ['extra_args']:
            environ['report_kinds'] = ['HIDDEN']

        problem.controller.fill_evaluation_environ(environ)

    def get_supported_extra_args(self, submission):
        """Returns dict of all values which can be provided in extra_args
           argument to the judge method.
        """
        return {'hidden_judge': _("Visible only for admins")}

    def judge(self, submission, extra_args=None):
        environ = {}
        environ['extra_args'] = extra_args or {}
        self.fill_evaluation_environ(environ, submission)

        extra_steps = [
                ('update_report_statuses',
                    'oioioi.contests.handlers.update_report_statuses'),
                ('update_submission_score',
                    'oioioi.contests.handlers.update_submission_score'),
                ('update_user_results',
                    'oioioi.contests.handlers.update_user_results'),
                ('call_submission_judged',
                    'oioioi.contests.handlers.call_submission_judged'),
                ('dump_final_env',
                    'oioioi.evalmgr.handlers.dump_env',
                    dict(message='Finished evaluation')),
            ]

        environ.setdefault('error_handlers', [])
        environ['error_handlers'].append(('create_error_report',
                    'oioioi.contests.handlers.create_error_report'))

        if settings.MAIL_ADMINS_ON_GRADING_ERROR:
            environ['error_handlers'].append(('mail_admins_on_error',
                        'oioioi.contests.handlers.mail_admins_on_error'))

        environ['error_handlers'].extend(extra_steps)
        environ['error_handlers'].append(('error_handled',
                    'oioioi.evalmgr.handlers.error_handled'))

        environ['recipe'].extend(extra_steps)

        logger.debug("Judging submission #%d with environ:\n %s",
                submission.id, pprint.pformat(environ, indent=4))
        async_result = evalmgr.evalmgr_job.delay(environ)

    def submission_judged(self, submission):
        pass

    def _activate_newest_report(self, submission, queryset, kind=None):
        """Activates the newest report.

           Previously active reports are set to ``SUPERSEDED``. Reports which
           are neither ``INACTIVE``, ``ACTIVE`` nor ``SUPERSEDED`` are not
           changed.

           :ptype kind: str, list, tuple or ``None``
           :param kind: If specified, only reports of the given kind(s) will be
                        considered.
        """
        try:
            if kind is None:
                pass
            elif isinstance(kind, basestring):
                queryset = queryset.filter(kind=kind)
            elif isinstance(kind, (list, tuple)):
                queryset = queryset.filter(kind__in=kind)
            else:
                raise TypeError("invalid type parameter kind in "
                        "_activate_newest_report: %r", type(kind))
            latest = queryset \
                    .select_for_update() \
                    .filter(status__in=('INACTIVE', 'ACTIVE', 'SUPERSEDED')) \
                    .latest()
            queryset.filter(status='ACTIVE').update(status='SUPERSEDED')
            latest.status = 'ACTIVE'
            latest.save()
        except ObjectDoesNotExist:
            pass

    def update_report_statuses(self, submission, queryset):
        """Updates statuses of reports for the newly judged submission.

           Usually this involves looking at reports and deciding which should
           be ``ACTIVE`` and which should be ``SUPERSEDED``.

           :param submission: an instance of
                              :class:`oioioi.contests.models.Submission`
           :param queryset: a queryset returning reports for the submission
        """
        self._activate_newest_report(submission, queryset)

    def update_submission_score(self, submission):
        """Updates status, score and comment in a submission.

           Usually this involves looking at active reports and aggregating
           information from them.
        """
        raise NotImplementedError

    def update_user_result_for_problem(self, result):
        """Updates a :class:`~oioioi.contests.models.UserResultForProblem`.

           Usually this involves looking at submissions and aggregating scores
           from them. Default implementation takes the latest submission which
           has a score and copies it to the result.
        """
        try:
            latest_submission = Submission.objects \
                .filter(problem_instance=result.problem_instance) \
                .filter(user=result.user) \
                .filter(score__isnull=False) \
                .filter(kind='NORMAL') \
                .latest()
            try:
                report = SubmissionReport.objects.get(
                        submission=latest_submission, status='ACTIVE',
                        kind='NORMAL')
            except SubmissionReport.DoesNotExist:
                report = None
            result.score = latest_submission.score
            result.status = latest_submission.status
            result.submission_report = report
        except Submission.DoesNotExist:
            result.score = None
            result.status = None
            result.submission_report = None
        result.save()

    def _sum_scores(self, scores):
        scores = [s for s in scores if s is not None]
        return scores and sum(scores[1:], scores[0]) or None

    def update_user_result_for_round(self, result):
        """Updates a :class:`~oioioi.contests.models.UserResultForRound`.

           Usually this involves looking at user's results for problems and
           aggregating scores from them. Default implementation sums the
           scores.
        """
        scores = UserResultForProblem.objects \
                .filter(user=result.user) \
                .filter(problem_instance__round=result.round) \
                .values_list('score', flat=True)
        result.score = self._sum_scores(map(ScoreValue.deserialize, scores))
        result.save()

    def update_user_result_for_contest(self, result):
        """Updates a :class:`~oioioi.contests.models.UserResultForContest`.

           Usually this involves looking at user's results for rounds and
           aggregating scores from them. Default implementation sums the
           scores.
        """
        scores = UserResultForRound.objects \
                .filter(user=result.user) \
                .filter(round__contest=result.contest) \
                .values_list('score', flat=True)
        result.score = self._sum_scores(map(ScoreValue.deserialize, scores))
        result.save()

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

        # We do this in three separate transactions, because in some database
        # engines (namely MySQL in REPEATABLE READ transaction isolation level)
        # data changed by a transaction is not visible in subsequent SELECTs
        # even in the same transaction.

        # First: UserResultForProblem
        with transaction.commit_on_success():
            result, created = UserResultForProblem.objects.select_for_update() \
                .get_or_create(user=user, problem_instance=problem_instance)
            self.update_user_result_for_problem(result)

        # Second: UserResultForRound
        with transaction.commit_on_success():
            result, created = UserResultForRound.objects.select_for_update() \
                .get_or_create(user=user, round=round)
            self.update_user_result_for_round(result)

        # Third: UserResultForContest
        with transaction.commit_on_success():
            result, created = UserResultForContest.objects.select_for_update() \
                .get_or_create(user=user, contest=contest)
            self.update_user_result_for_contest(result)

    def filter_my_visible_submissions(self, request, queryset):
        """Returns the submissions which the user should see in the
           "My submissions" view.

           The default implementation returns all submissions belonging to
           the user for the problems that are visible.

           Should return the updated queryset.
        """
        if not request.user.is_authenticated():
            return queryset.none()
        qs = queryset.filter(user=request.user) \
            .filter(problem_instance__in=visible_problem_instances(request))
        if is_contest_admin(request):
            return qs
        else:
            return qs.filter(date__lte=request.timestamp)

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
        """Determines whether a user can see one of his/her submissions'
           status.

           Default implementation delegates to :meth:
           :meth:`~ContestController.results_visible`.

           :rtype: bool
           """
        return self.results_visible(request, submission)

    def can_see_submission_score(self, request, submission):
        """Determines whether a user can see one of his/her submissions'
           score.

           Default implementation delegates to :meth:
           :meth:`~ContestController.results_visible`.

           :rtype: bool
        """
        return self.results_visible(request, submission)

    def can_see_submission_comment(self, request, submission):
        """Determines whether a user can see one of his/her submissions'
           comment.

           Default implementation delegates to :meth:
           :meth:`~ContestController.results_visible`.

           :rtype: bool
        """
        return self.results_visible(request, submission)

    def render_submission_date(self, submission):
        """Returns a human-readable representation of the submission date.

           In some contests it is more reasonable to show time elapsed since
           the contest start, in others it's better to just show the wall
           clock time.

           The default implementation returns the wall clock time.
        """
        localtime = timezone.localtime(submission.date)
        return localtime.strftime('%Y-%m-%d %H:%M:%S')

    def render_submission_score(self, submission):
        """Returns a human-readable representation of the submission score.

           The default implementation returns the Unicode representation of
           ``submission.score``.
        """
        return unicode(submission.score)

    def render_submission(self, request, submission):
        """Renders the given submission to HTML.

           This is usually a table with some basic submission info,
           source code download etc., displayed on the top of the
           submission details view, above the reports.
        """
        raise NotImplementedError

    def render_submission_footer(self, request, submission):
        """Renders the given submission footer to HTML.

           Footer is shown under the submission reports.
           The default implementation returns an empty string.
        """
        return mark_safe("")

    def render_report(self, request, report):
        """Renders the given report to HTML.

           Default implementatiion suports only rendering reports of
           kind ``FAILURE`` and raises :py:exc:`NotImplementedError`
           otherwise.
        """
        if report.kind == 'FAILURE':
            failure_report = \
                    FailureReport.objects.get(submission_report=report)
            message = failure_report.message
            environ = json.loads(failure_report.json_environ)
            if not environ.get('recipe'):
                next_step = '(none)'
            else:
                next_step = repr(environ['recipe'][0])
            del environ['recipe']
            del environ['error_handlers']
            environ = pprint.pformat(environ, indent=4)
            return render_to_string('contests/failure_report.html',
                    context_instance=RequestContext(request,
                        {'message': message, 'next_step': next_step,
                            'environ': environ}))
        else:
            raise NotImplementedError

    def adjust_contest(self):
        """Called when a (usually new) contest has just got the controller
           attached or after the contest has been modified."""
        pass

    def valid_kinds_for_submission(self, submission):
        """Returns list of all valid kinds we can change to
           for the given submission.

           Default implementation supports only kinds
           ``NORMAL``, ``IGNORED``, ``SUSPECTED``.
        """
        valid = ['NORMAL', 'IGNORED', 'SUSPECTED']
        if submission.kind != 'SUSPECTED':
            return [v for v in valid if v != 'SUSPECTED']
        if submission.kind in valid:
            return valid
        return []

    def change_submission_kind(self, submission, kind):
        """Changes kind of the submission. Also updates user reports for
           problem, round and contest which may contain given submission.
        """
        assert kind in self.valid_kinds_for_submission(submission)
        old_kind = submission.kind
        submission.kind = kind
        submission.save()
        if old_kind == 'SUSPECTED' and kind != 'SUSPECTED':
            self.judge(submission)
        if submission.user:
            self.update_user_results(submission.user,
                    submission.problem_instance)

    def mixins_for_admin(self):
        """Returns an iterable of mixins to add to the default
           :class:`oioioi.contests.admin.ContestAdmin` for
           this particular contest.

           The default implementation returns an empty tuple.
        """
        return ()
