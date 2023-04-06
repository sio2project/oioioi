# pylint: disable=undefined-loop-variable
import datetime
import itertools
from collections import defaultdict
from operator import attrgetter, itemgetter  # pylint: disable=E0611

from django.conf import settings
from django.contrib.auth.models import AnonymousUser, User
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.utils.translation import gettext_noop

from oioioi.acm.score import ACMScore, BinaryScore, format_time
from oioioi.contests.models import (
    ProblemInstance,
    Submission,
    SubmissionReport,
    UserResultForProblem,
)
from oioioi.contests.utils import rounds_times
from oioioi.participants.controllers import (
    OpenParticipantsController,
    ParticipantsController,
)
from oioioi.participants.utils import is_participant
from oioioi.programs.controllers import ProgrammingContestController
from oioioi.rankings.controllers import CONTEST_RANKING_KEY, DefaultRankingController

IGNORED_STATUSES = ['CE', 'SE', '?']


class ACMContestController(ProgrammingContestController):
    description = _("ACM style contest")
    create_forum = False

    def registration_controller(self):
        return ParticipantsController(self.contest)

    def get_round_freeze_time(self, round):
        """Returns time after which any further updates should be non-public."""
        if not round.end_date:
            return None
        if round.is_trial:
            frozen_ranking_minutes = 0
        else:
            frozen_ranking_minutes = 60

        return round.end_date - datetime.timedelta(minutes=frozen_ranking_minutes)

    def fill_evaluation_environ(self, environ, submission):
        environ['group_scorer'] = 'oioioi.acm.utils.acm_group_scorer'
        environ['test_scorer'] = 'oioioi.acm.utils.acm_test_scorer'
        environ['score_aggregator'] = 'oioioi.acm.utils.acm_score_aggregator'
        environ['report_kinds'] = ['FULL']

        super(ACMContestController, self).fill_evaluation_environ(environ, submission)

    def update_report_statuses(self, submission, queryset):
        if submission.kind == 'TESTRUN':
            self._activate_newest_report(submission, queryset,
                    kind=['TESTRUN', 'FAILURE'])
            return

        self._activate_newest_report(submission, queryset, kind=['FULL', 'FAILURE'])

    def update_submission_score(self, submission):
        if submission.kind == 'TESTRUN':
            super(ACMContestController, self).update_submission_score(submission)
            return
        try:
            report = SubmissionReport.objects.get(
                submission=submission, status='ACTIVE', kind='FULL'
            )
            score_report = report.score_report
            submission.max_score = score_report.max_score
            if score_report.status in IGNORED_STATUSES:
                submission.score = None
            else:
                submission.score = BinaryScore(score_report.status == 'OK')
            submission.status = score_report.status
        except SubmissionReport.DoesNotExist:
            submission.score = None
            submission.max_score = None
            if SubmissionReport.objects.filter(
                submission=submission, status='ACTIVE', kind='FAILURE'
            ):
                submission.status = 'SE'
            else:
                submission.status = '?'
        submission.save()

    def get_submission_relative_time(self, submission):
        # FIXME: SIO-1387 RoundTimes shouldn't require request
        # Workaround by mock Request object
        class DummyRequest(object):
            def __init__(self, user):
                self.user = user or AnonymousUser()

        rtimes = rounds_times(
            DummyRequest(submission.user or AnonymousUser()), self.contest
        )
        round_start = rtimes[submission.problem_instance.round].get_start()
        submission_time = submission.date - round_start
        # Python2.6 does not support submission_time.total_seconds()
        seconds = submission_time.days * 24 * 3600 + submission_time.seconds
        return max(0, seconds)

    def _fill_user_result_for_problem(self, result, pi_submissions):
        if pi_submissions:
            for penalties_count, submission in enumerate(pi_submissions, 1):
                if submission.status == 'IGN':
                    # We have found IGNORED submission before accepted one.
                    # This means, that some other
                    # submission is no longer accepted
                    self.update_submission_score(submission)
                if submission.status == 'OK':
                    # ``submission`` and ``penalties_count`` variables preserve
                    #  their last value after the loop
                    break

            solved = int(submission.status == 'OK')
            score = ACMScore(
                problems_solved=solved,
                penalties_count=(penalties_count - solved),
                time_passed=self.get_submission_relative_time(submission),
            )
            result.score = score
            result.status = submission.status
            return submission

        else:
            result.score = None
            result.status = None
            return None

    def update_user_result_for_problem(self, result):
        submissions = (
            Submission.objects.filter(
                problem_instance=result.problem_instance,
                user=result.user,
                kind='NORMAL',
            )
            .exclude(status__in=IGNORED_STATUSES)
            .order_by('date')
        )

        last_submission = self._fill_user_result_for_problem(result, submissions)
        if last_submission:
            result.submission_report = last_submission.submissionreport_set.get(
                status='ACTIVE', kind='FULL'
            )

            if last_submission.status == 'OK':
                # FIXME: May not ignore submissions with admin-hacked same-date
                submissions.filter(date__gt=last_submission.date).update(
                    status='IGN', score=None
                )
        else:
            result.submission_report = None

    def results_visible(self, request, submission):
        return False

    def get_visible_reports_kinds(self, request, submission):
        if submission.status == 'CE':
            return ['FULL', 'TESTRUN']
        else:
            return ['TESTRUN']

    def can_see_submission_score(self, request, submission):
        return True

    def can_see_submission_status(self, request, submission):
        return True

    def render_submission_date(self, submission, shortened=False):
        return format_time(self.get_submission_relative_time(submission))

    def ranking_controller(self):
        return ACMRankingController(self.contest)

    def can_see_round(self, request_or_context, round):
        context = self.make_context(request_or_context)
        if context.is_admin:
            return True
        rtimes = self.get_round_times(request_or_context, round)
        return rtimes.is_active(context.timestamp)

    def get_default_safe_exec_mode(self):
        return 'cpu'


class ACMOpenContestController(ACMContestController):
    description = _("ACM style contest (open)")

    def registration_controller(self):
        return OpenParticipantsController(self.contest)

    def can_submit(self, request, problem_instance, check_round_times=True):
        if request.user.is_anonymous:
            return False
        if request.user.has_perm('contests.contest_admin', self.contest):
            return True
        if not is_participant(request):
            return False
        return super(ACMOpenContestController, self).can_submit(
            request, problem_instance, check_round_times
        )


class _FakeUserResultForProblem(object):
    def __init__(self, user, problem_instance):
        self.problem_instance = problem_instance
        self.user = user

    @property
    def user_id(self):
        return self.user.id

    @property
    def problem_instance_id(self):
        return self.problem_instance.id

    def __repr__(self):
        return str(self.__dict__)


class ACMRankingController(DefaultRankingController):
    description = _("ACM style ranking")

    def _iter_rounds(self, can_see_all, timestamp, partial_key, request=None):
        ccontroller = self.contest.controller
        queryset = self.contest.round_set.all()
        if partial_key != CONTEST_RANKING_KEY:
            queryset = queryset.filter(id=partial_key)
        for round in queryset:
            times = ccontroller.get_round_times(request, round)
            if can_see_all or not times.is_future(timestamp):
                yield round

    def can_search_for_users(self):
        return False

    def _render_ranking_page(self, key, data, page):
        request = self._fake_request(page)
        data['is_admin'] = self.is_admin_key(key)
        return render_to_string('acm/acm_ranking.html', context=data, request=request)

    def _get_csv_header(self, key, data):
        header = [_("#"), _("Username"), _("First name"), _("Last name"), _("Solved")]
        for pi, _statement_visible in data['problem_instances']:
            header.append(pi.get_short_name_display())
        header.append(_("Sum"))
        return header

    def _get_csv_row(self, key, row):
        line = [
            row['place'],
            row['user'].username,
            row['user'].first_name,
            row['user'].last_name,
        ]
        line.append(row['sum'].problems_solved)
        line += [
            r.score.csv_repr() if r and r.score is not None else ''
            for r in row['results']
        ]
        line.append(row['sum'].total_time_repr())
        return line

    def filter_users_for_ranking(self, key, queryset):
        return self.contest.controller.registration_controller().filter_participants(
            queryset
        )

    def _get_old_results(self, freeze_time, pis, users):
        controller = self.contest.controller
        submissions = (
            Submission.objects.filter(
                problem_instance__in=pis,
                user__in=users,
                kind='NORMAL',
                date__lt=freeze_time,
            )
            .exclude(status__in=IGNORED_STATUSES)
            .select_related('user', 'problem_instance')
            .order_by('user', 'problem_instance', 'date')
        )
        results = []
        for user, user_submissions in itertools.groupby(
            submissions, attrgetter('user')
        ):
            for pi, user_pi_submissions in itertools.groupby(
                user_submissions, attrgetter('problem_instance')
            ):
                result = _FakeUserResultForProblem(user, pi)
                controller._fill_user_result_for_problem(result, user_pi_submissions)
                results.append(result)
        return results

    def serialize_ranking(self, key):
        controller = self.contest.controller
        rounds = list(self._rounds_for_key(key))
        # If at least one visible round is not trial we don't want to show
        # trial rounds in default ranking.
        if self.get_partial_key(key) == CONTEST_RANKING_KEY:
            not_trial = [r for r in rounds if not r.is_trial]
            if not_trial:
                rounds = not_trial

        freeze_times = [controller.get_round_freeze_time(round) for round in rounds]

        pis = list(
            ProblemInstance.objects.filter(round__in=rounds)
            .select_related('problem')
            .prefetch_related('round')
        )
        rtopis = defaultdict(lambda: [])

        for pi in pis:
            rtopis[pi.round].append(pi)

        users = self.filter_users_for_ranking(key, User.objects.all())

        results = []
        ccontroller = self.contest.controller

        frozen = False
        for round, freeze_time in zip(rounds, freeze_times):
            rpis = rtopis[round]
            rtimes = ccontroller.get_round_times(None, round)
            now = timezone.now()
            if (
                freeze_time is None
                or self.is_admin_key(key)
                or rtimes.results_visible(now)
                or now <= freeze_time
            ):
                results += (
                    UserResultForProblem.objects.filter(
                        problem_instance__in=rpis, user__in=users
                    )
                    .prefetch_related('problem_instance__round')
                    .select_related(
                        'submission_report',
                        'problem_instance',
                        'problem_instance__contest',
                    )
                )
            else:
                results += self._get_old_results(freeze_time, rpis, users)
                frozen = True

        data = self._get_users_results(pis, results, rounds, users)
        self._assign_places(data, itemgetter('sum'))
        return {
            'rows': data,
            'problem_instances': self._get_pis_with_visibility(key, pis),
            'frozen': frozen,
            'participants_on_page': getattr(settings, 'PARTICIPANTS_ON_PAGE', 100),
        }


class NotificationsMixinForACMContestController(object):
    """Modifies default contest notification settings from
    :class:`~oioioi.contests.controllers.NotificationsMixinForContestController`.
    It enables sending notifications about new public messages to all
    participants and modifies submission notification messages so that
    """

    def users_to_receive_public_message_notification(self):
        return self.registration_controller().filter_participants(User.objects.all())

    def get_notification_message_submission_judged(self, submission):
        if submission.score is not None and submission.score.accepted:
            return gettext_noop(
                "Your submission for task %(short_name)s"
                " is accepted. Congratulations!"
            )
        else:
            return gettext_noop(
                "Your submission for task %(short_name)s is not accepted."
            )


ACMContestController.mix_in(NotificationsMixinForACMContestController)
