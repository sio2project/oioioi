import json
import logging
import pprint

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.db.models import Max, Q
from django.db.models.signals import post_delete
from django.dispatch import receiver
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _, gettext_noop
from oioioi.base.utils import ObjectWithMixins, RegisteredSubclassesBase
from oioioi.contests.models import (
    FailureReport,
    ScoreReport,
    Submission,
    SubmissionReport,
    UserResultForProblem,
)
from oioioi.contests.scores import IntegerScore
from oioioi.evalmgr.tasks import create_environ, delay_environ
from oioioi.problems.models import ProblemStatistics, UserStatistics
from oioioi.problems.utils import can_admin_problem

logger = logging.getLogger(__name__)


class ProblemController(RegisteredSubclassesBase, ObjectWithMixins):
    """Defines rules for handling specific problem.

    Every method should:

    * be called from contest controller

    * or be specific for problems that this controller controls

    Please note that a global problem instance exists for each problem.
    That problem instance has no contest (``contest`` is ``None``),
    so methods can't be overridden by a contest controller which means they
    behave in a default way.
    """

    modules_with_subclasses = ['controllers']
    abstract = True

    def __init__(self, problem):
        self.problem = problem

    def adjust_problem(self):
        """Called whan a (usually new) problem has just got the controller
        attached or after the problem has been modified.
        """
        pass

    def get_default_submission_kind(self, request, problem_instance):
        """Returns default kind of newly created submission by the current
        user.

        The default implementation returns ``'IGNORED'`` for
        problem admins. In other cases it returns ``'NORMAL'``.
        """
        if can_admin_problem(request, problem_instance.problem):
            return 'IGNORED'
        return 'NORMAL'

    def get_submissions_limit(self, request, problem_instance, kind='NORMAL'):
        # in the future it should always return None as submissions limit
        # for main_problem_instance (without contest) makes no sense and
        # rest of logic should  be moved to contest controller
        problem = problem_instance.problem

        if (
            problem_instance.contest is None
            or can_admin_problem(request, problem)
            or kind == 'IGNORED'
        ):
            return None
        return problem_instance.submissions_limit

    def can_submit(self, request, problem_instance, check_round_times=True):
        """Determines if the current user is allowed to submit a solution for
        the given problem.

        The default implementation checks if the user is not anonymous.
        Subclasses should also call this default implementation.
        """
        if request.user.is_anonymous:
            return False
        return True

    def is_submissions_limit_exceeded(self, request, problem_instance, kind):
        submissions_limit = problem_instance.controller.get_submissions_limit(
            request, problem_instance, kind
        )
        if not submissions_limit:
            return False

        submissions_number = Submission.objects.filter(
            user=request.user, problem_instance__id=problem_instance.id, kind=kind
        ).count()
        return submissions_number >= submissions_limit

    def get_submissions_left(self, request, problem_instance, kind='NORMAL'):
        """Returns number of submissions left until reaching problem limit"""
        if request.user.is_anonymous:
            return None

        submissions_limit = problem_instance.controller.get_submissions_limit(
            request, problem_instance, kind
        )
        if not submissions_limit:
            return None
        submissions_number = Submission.objects.filter(
            user=request.user, problem_instance__id=problem_instance.id, kind=kind
        ).count()

        return max(0, submissions_limit - submissions_number)

    def fill_evaluation_environ(self, environ, submission, **kwargs):
        """Fills a minimal environment with evaluation receipt and other values
        required by the evaluation machinery.

        Passed ``environ`` should already contain entries for the actiual
        data to be judged (for example the source file to evaluate).

        Details on which keys need to be present should be specified by
        particular subclasses.

        As the result, ``environ`` will be filled at least with a suitable
        evaluation ``recipe``.
        """
        raise NotImplementedError

    def finalize_evaluation_environment(self, environ):
        """This method gets called right before the environ becomes scheduled
        in the queue. It gets called only for submissions send without
        a contest

        This hook exists for inserting extra handlers to the recipe before
        judging the solution.
        """
        pass

    def judge(self, submission, extra_args=None, is_rejudge=False):
        environ = create_environ()
        environ['extra_args'] = extra_args or {}
        environ['is_rejudge'] = is_rejudge
        picontroller = submission.problem_instance.controller

        picontroller.fill_evaluation_environ(environ, submission)

        extra_steps = (
            [
                (
                    'update_report_statuses',
                    'oioioi.contests.handlers.update_report_statuses',
                ),
                (
                    'update_submission_score',
                    'oioioi.contests.handlers.update_submission_score',
                ),
                ('update_user_results', 'oioioi.contests.handlers.update_user_results'),
            ]
            + (
                [
                    (
                        'update_problem_statistics',
                        'oioioi.contests.handlers.update_problem_statistics',
                    )
                ]
                if settings.PROBLEM_STATISTICS_AVAILABLE
                else []
            )
            + [
                (
                    'call_submission_judged',
                    'oioioi.contests.handlers.call_submission_judged',
                ),
                (
                    'send_notification_submission_judged',
                    'oioioi.contests.handlers.send_notification_judged',
                ),
                (
                    'dump_final_env',
                    'oioioi.evalmgr.handlers.dump_env',
                    dict(message='Finished evaluation'),
                ),
            ]
        )

        environ.setdefault('error_handlers', [])
        environ['error_handlers'].append(
            ('create_error_report', 'oioioi.contests.handlers.create_error_report')
        )

        if settings.MAIL_ADMINS_ON_GRADING_ERROR:
            environ['error_handlers'].append(
                (
                    'mail_admins_on_error',
                    'oioioi.contests.handlers.mail_admins_on_error',
                )
            )

        environ['error_handlers'].extend(extra_steps)
        environ['error_handlers'].append(
            ('error_handled', 'oioioi.evalmgr.handlers.error_handled')
        )

        environ['recipe'].extend(extra_steps)

        picontroller.finalize_evaluation_environment(environ)

        environ['recipe'].insert(
            0,
            (
                'wait_for_submission_in_db',
                'oioioi.contests.handlers.wait_for_submission_in_db',
            ),
        )

        evalmgr_extra_args = environ.get('evalmgr_extra_args', {})
        logger.debug(
            "Judging submission #%d with environ:\n %s",
            submission.id,
            pprint.pformat(environ, indent=4),
        )
        delay_environ(environ, **evalmgr_extra_args)

    def mixins_for_admin(self):
        """Returns an iterable of mixins to add to the default
        :class:`oioioi.problems.admin.ProblemAdmin` for
        this particular problem.

        The default implementation returns an empty tuple.
        """
        return ()

    def update_user_result_for_problem(self, result):
        """Updates a :class:`~oioioi.contests.models.UserResultForProblem`.

        Usually this involves looking at submissions and aggregating scores
        from them. Default implementation takes the latest submission which
        has a score and copies it to the result.

        Saving the ``result`` is a responsibility of the caller.
        """
        try:
            latest_submission = (
                Submission.objects.filter(problem_instance=result.problem_instance)
                .filter(user=result.user)
                .filter(score__isnull=False)
                .filter(kind='NORMAL')
                .latest()
            )
            try:
                report = SubmissionReport.objects.get(
                    submission=latest_submission, status='ACTIVE', kind='NORMAL'
                )
            except SubmissionReport.DoesNotExist:
                report = None
            result.score = latest_submission.score
            result.status = latest_submission.status
            result.submission_report = report
        except Submission.DoesNotExist:
            result.score = None
            result.status = None
            result.submission_report = None

    def update_problem_statistics(
        self, problem_statistics, user_statistics, submission
    ):
        """Updates :class:`~oioioi.problems.models.ProblemStatistics` and
        :class:`~oioioi.problems.models.UserStatistics` with data from a new
        :class:`~oioioi.contests.models.Submission`.

        This is called when a new submission is checked, and for performance
        reasons performs as few database queries as possible. The default
        implementation only checks the submission report kind, and retrieves
        the score report for the submission.

        By default, only ACTIVE and NORMAL submissions are counted for
        statistics. If you change this behaviour make sure to also update
        :func:`~oioioi.problems.controllers.ProblemController.change_submission_kind`.

        Saving both statistics objects is a responsibility of the caller.
        """
        # Do not record ignored or hidden solutions
        if submission.kind != 'NORMAL':
            return
        try:
            # Get most recent report
            report = SubmissionReport.objects.get(
                submission=submission, status='ACTIVE', kind='NORMAL'
            )
            score_report = ScoreReport.objects.get(submission_report=report)

            if not user_statistics.has_submitted:
                user_statistics.has_submitted = True
                problem_statistics.submitted += 1

            # Submission may be without final tests or just broken
            # It's better to use submission.score instead of score_report.score,
            # since for imported submissions the score_report.score may be NULL
            if submission.score is None:
                assert score_report.score is None
                return
            if score_report.score is not None:
                assert submission.score == score_report.score

            # Submission may be imported/from before max_score was implemented
            # The best we can try doing is looking at the tests for the problem
            # instance - if the tests are also broken we are doomed anyway
            if score_report.max_score is None:
                test_group_max_scores = (
                    submission.problem_instance.test_set.filter(kind='NORMAL')
                    .values_list('group')
                    .annotate(group_max_score=Max('max_score'))
                )
                max_score = sum(dict(test_group_max_scores).values())
            else:
                max_score = score_report.max_score.to_int()

            # Submission may have max_score that's invalid for statistics
            if max_score == 0:
                return

            if not user_statistics.has_solved and submission.score >= max_score:
                user_statistics.has_solved = True
                problem_statistics.solved += 1

            problem_statistics._best_score_sum -= user_statistics.best_score
            # Scale the score to a percentage of max_score
            user_statistics.best_score = max(
                user_statistics.best_score,
                100 * min(max_score, submission.score.to_int()) / max_score,
            )
            problem_statistics._best_score_sum += user_statistics.best_score

            # problem_statistics.submitted won't be 0 because we have a submit
            problem_statistics.avg_best_score = (
                problem_statistics._best_score_sum / problem_statistics.submitted
            )

        except SubmissionReport.DoesNotExist:
            pass

    @transaction.atomic
    def recalculate_statistics_for_user(self, user):
        """Recalculates user's statistics for this problem controller's problem

        Sometimes (for example when a submission's type changes) we can't
        update user statistics quickly, and need to recalculate them.
        This function by default erases the user statistics for the problem
        and recalculates them from all of this user's submissions to every
        probleminstance of the problem.
        """
        if not settings.PROBLEM_STATISTICS_AVAILABLE:
            return

        (
            problem_statistics,
            created,
        ) = ProblemStatistics.objects.select_for_update().get_or_create(
            problem=self.problem
        )
        (
            user_statistics,
            created,
        ) = UserStatistics.objects.select_for_update().get_or_create(
            problem_statistics=problem_statistics, user=user
        )

        if not created:
            # Rollback the user's statistics
            if user_statistics.has_submitted:
                problem_statistics.submitted -= 1
            if user_statistics.has_solved:
                problem_statistics.solved -= 1
            problem_statistics._best_score_sum -= user_statistics.best_score
            if problem_statistics.submitted == 0:
                problem_statistics.avg_best_score = 0
            else:
                problem_statistics.avg_best_score = (
                    problem_statistics._best_score_sum / problem_statistics.submitted
                )
            user_statistics.delete()
            (
                user_statistics,
                created,
            ) = UserStatistics.objects.select_for_update().get_or_create(
                problem_statistics=problem_statistics, user=user
            )

        # Recreate statistics from every relevant submission one by one
        user_submissions = Submission.objects.filter(
            user=user, problem_instance__problem=self.problem
        )
        for submission in user_submissions:
            submission.problem_instance.controller.update_problem_statistics(
                problem_statistics, user_statistics, submission
            )
        user_statistics.save()
        problem_statistics.save()

    @staticmethod
    @receiver(post_delete, sender=Submission)
    def recalculate_statistics_on_submission_deleted(instance, **kwargs):
        if instance.user:
            instance.problem_instance.problem.controller.recalculate_statistics_for_user(
                instance.user
            )

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
            elif isinstance(kind, str):
                queryset = queryset.filter(kind=kind)
            elif isinstance(kind, (list, tuple)):
                queryset = queryset.filter(kind__in=kind)
            else:
                raise TypeError(
                    "invalid type parameter kind in _activate_newest_report: %r",
                    type(kind),
                )
            latest = (
                queryset.select_for_update()
                .filter(status__in=('INACTIVE', 'ACTIVE', 'SUPERSEDED'))
                .latest()
            )
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
        controller = submission.problem_instance.controller
        controller._activate_newest_report(
            submission, queryset, kind=['NORMAL', 'FAILURE']
        )
        controller._activate_newest_report(submission, queryset, kind=['INITIAL'])
        controller._activate_newest_report(submission, queryset, kind=['USER_OUTS'])

    def update_user_results(self, user, problem_instance):
        """Updates score for problem instance.

        Usually this method creates instances (if they don't exist) of:
        * :class:`~oioioi.contests.models.UserResultForProblem`

        and then calls proper methods of ProblemController to update them.
        """

        with transaction.atomic():
            (
                result,
                created,
            ) = UserResultForProblem.objects.select_for_update().get_or_create(
                user=user, problem_instance=problem_instance
            )
            problem_instance.controller.update_user_result_for_problem(result)
            result.save()

    def validate_submission_form(self, request, problem_instance, form, cleaned_data):
        return cleaned_data

    def adjust_submission_form(self, request, form, problem_instance):
        pass

    def create_submission(self, request, problem_instance, form_data, **kwargs):
        raise NotImplementedError

    def render_submission_date(self, submission, shortened=False):
        """Returns a human-readable representation of the submission date.

        In some contests it is more reasonable to show time elapsed since
        the contest start, in others it's better to just show the wall
        clock time.

        The default implementation returns the wall clock time.
        """
        localtime = timezone.localtime(submission.date)
        if shortened:
            return localtime.strftime('%m-%d %H:%M:%S')
        return localtime.strftime('%Y-%m-%d %H:%M:%S')

    def render_submission_score(self, submission):
        """Returns a human-readable representation of the submission score.

        The default implementation returns the Unicode representation of
        ``submission.score``.
        """
        return str(submission.score)

    def get_supported_extra_args(self, submission):
        """Returns dict of all values which can be provided in extra_args
        argument to the judge method.
        """
        return {'hidden_judge': _("Visible only for admins")}

    def render_submission_footer(self, request, submission):
        """Renders the given submission footer to HTML.

        Footer is shown under the submission reports.
        The default implementation returns an empty string.
        """
        return mark_safe("")

    def render_report(self, request, report):
        """Renders the given report to HTML.

        Default implementation supports only rendering reports of
        kind ``FAILURE`` and raises :py:exc:`NotImplementedError`
        otherwise.
        """
        if report.kind == 'FAILURE':
            failure_report = FailureReport.objects.get(submission_report=report)
            message = failure_report.message
            environ = json.loads(failure_report.json_environ)
            if not environ.get('recipe'):
                next_step = '(none)'
            else:
                next_step = repr(environ['recipe'][0])
            del environ['recipe']
            del environ['error_handlers']
            environ = pprint.pformat(environ, indent=4)
            return render_to_string(
                'contests/failure_report.html',
                request=request,
                context={
                    'message': message,
                    'next_step': next_step,
                    'environ': environ,
                },
            )
        else:
            raise NotImplementedError

    def filter_visible_reports(self, request, submission, queryset):
        """Determines which reports the user should be able to see.

        It needs to check whether the submission is visible to the user
        and submission is submitted without contest.

        :param request: Django request
        :param submission: instance of
                           :class:`~oioioi.contests.models.Submission`
        :param queryset: a queryset, initially filtered at least to
                           select only given submission's reports
        :returns: updated queryset
        """
        assert not submission.problem_instance.contest
        problem = submission.problem_instance.problem
        if can_admin_problem(request, problem):
            return queryset
        return queryset.filter(status='ACTIVE', kind='NORMAL')

    def valid_kinds_for_submission(self, submission):
        """Returns list of all valid kinds we can change to
        for the given submission.

        Default implementation supports only kinds
        ``NORMAL``, ``IGNORED``, ``SUSPECTED``, 'IGNORED_HIDDEN'.
        """
        valid = ['NORMAL', 'IGNORED', 'SUSPECTED', 'IGNORED_HIDDEN']
        if submission.kind != 'SUSPECTED':
            return [v for v in valid if v != 'SUSPECTED']
        if submission.kind in valid:
            return valid
        return []

    def results_visible(self, request, submission):
        """Determines whether it is a good time to show the submission's
        results.

        This method is not used directly in any code outside of the
        controllers. It's a helper method used in a number of other
        controller methods, as described.

        The default implementations returns ``True``.
        """
        return True

    def can_see_submission_status(self, request, submission):
        """Determines whether a user can see one of his/her submissions'
        status.

        Default implementation delegates to :meth:
        :meth:`~ProblemInstanceController.results_visible`.

        :rtype: bool
        """
        return submission.problem_instance.controller.results_visible(
            request, submission
        )

    def can_see_submission_score(self, request, submission):
        """Determines whether a user can see one of his/her submissions'
        score.

        Default implementation delegates to :meth:
        :meth:`~ProblemInstanceController.results_visible`.

        :rtype: bool
        """
        return submission.problem_instance.controller.results_visible(
            request, submission
        )

    def can_see_submission_comment(self, request, submission):
        """Determines whether a user can see one of his/her submissions'
        comment.

        Default implementation delegates to :meth:
        :meth:`~ProblemInstanceController.results_visible`.

        :rtype: bool
        """
        return submission.problem_instance.controller.results_visible(
            request, submission
        )

    def change_submission_kind(self, submission, kind):
        """Changes kind of the submission, updates user reports for problem,
        round and contest which may contain given submission, and
        updates statistics for the submission's user if necessary.
        """
        assert (
            kind
            in submission.problem_instance.controller.valid_kinds_for_submission(
                submission
            )
        )
        old_kind = submission.kind
        submission.kind = kind
        submission.save()
        if old_kind == 'SUSPECTED' and kind != 'SUSPECTED':
            submission.problem_instance.controller.judge(submission, is_rejudge=True)
        if submission.user:
            submission.problem_instance.controller.update_user_results(
                submission.user, submission.problem_instance
            )
            if old_kind == 'NORMAL' or kind == 'NORMAL':
                submission.problem_instance.problem.controller.recalculate_statistics_for_user(
                    submission.user
                )

    def _is_partial_score(self, test_report):
        if not test_report:
            return False
        if isinstance(test_report.score, IntegerScore):
            return test_report.score.value != test_report.max_score.value
        return False

    def filter_my_visible_submissions(self, request, queryset, filter_user=True):
        """Returns the submissions which the user should see in the
        problemset in "My submissions" view.

        The default implementation returns all submissions belonging to
        the user for current problem except for author, who
        gets all his submissions.

        Should return the updated queryset.
        """
        if not request.user.is_authenticated:
            return queryset.none()
        qs = queryset.filter(problem_instance=self.problem.main_problem_instance)
        if can_admin_problem(request, self.problem):
            if filter_user:
                qs = qs.filter(Q(user=request.user) | Q(user__isnull=True))
            return qs
        else:
            if filter_user:
                qs = qs.filter(user=request.user)
            return qs.filter(date__lte=request.timestamp).exclude(kind='IGNORED_HIDDEN')

    def get_extra_problem_site_actions(self, problem):
        """Returns a list of tuples (url, name)
        that will be displayed under actions in ProblemSite.
        """
        return []

    def supports_problem_statement(self):
        """If the ProblemController supports problem statement,
        opening the problem in a contest shows the associated problem
        statement or an information that it doesn't have one.
        On the other hand, if it doesn't support the problem statement,
        opening the problem redirects to submit solution page.
        """
        return True


    def get_notification_message_submission_judged(self, submission):
        """Returns a message to show in a notification when a submission has
        been judged. It doesn't validate any permissions.
        """
        if submission.problem_instance.contest:
            message = gettext_noop(
                "%(contest_name)s, %(task_name)s: Your submission was judged.\n"
            )
        else:
            message = gettext_noop("%(task_name)s: Your submission was judged.\n")

        if submission.score is not None:
            message += gettext_noop("The score is %(score)s.")

        return message
