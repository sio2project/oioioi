# pylint: disable=W0631
# W0631 Using possibly undefined loop variable
import itertools
import datetime
from operator import attrgetter, itemgetter
from collections import defaultdict

from django.template.loader import render_to_string
from django.template import RequestContext
from django.contrib.auth.models import User
from django.utils.translation import ugettext_lazy as _

from oioioi.programs.controllers import ProgrammingContestController
from oioioi.rankings.controllers import DefaultRankingController, \
        CONTEST_RANKING_KEY
from oioioi.contests.models import SubmissionReport, Submission, \
        ProblemInstance, UserResultForProblem
from oioioi.acm.score import BinaryScore, format_time, ACMScore
from oioioi.contests.utils import is_contest_admin, rounds_times
from oioioi.participants.controllers import ParticipantsController


IGNORED_STATUSES = ['CE', 'SE', '?']


class ACMContestController(ProgrammingContestController):
    description = _("ACM style contest")
    create_forum = False

    def registration_controller(self):
        return ParticipantsController(self.contest)

    def get_round_freeze_time(self, round):
        """Returns time after which any further updates should be non-public.
        """
        if not round.end_date:
            return None
        if round.is_trial:
            frozen_ranking_minutes = 0
        else:
            frozen_ranking_minutes = 60

        return round.end_date - \
               datetime.timedelta(minutes=frozen_ranking_minutes)

    def fill_evaluation_environ(self, environ, submission):
        environ['group_scorer'] = 'oioioi.acm.utils.acm_group_scorer'
        environ['test_scorer'] = 'oioioi.acm.utils.acm_test_scorer'
        environ['score_aggregator'] = 'oioioi.acm.utils.acm_score_aggregator'
        environ['report_kinds'] = ['FULL']

        super(ACMContestController, self). \
                fill_evaluation_environ(environ, submission)

    def update_report_statuses(self, submission, queryset):
        self._activate_newest_report(submission, queryset,
            kind=['FULL', 'FAILURE'])

    def update_submission_score(self, submission):
        try:
            report = SubmissionReport.objects.get(submission=submission,
                    status='ACTIVE', kind='FULL')
            score_report = report.score_report
            if score_report.status in IGNORED_STATUSES:
                submission.score = None
            else:
                submission.score = BinaryScore(score_report.status == 'OK')
            submission.status = score_report.status
        except SubmissionReport.DoesNotExist:
            submission.score = None
            if SubmissionReport.objects.filter(submission=submission,
                    status='ACTIVE', kind='FAILURE'):
                submission.status = 'SE'
            else:
                submission.status = '?'
        submission.save()

    def get_submission_relative_time(self, submission):
        # FIXME: SIO-1387 RoundTimes shouldn't require request
        # Workaround by mock Request object
        class DummyRequest(object):
            def __init__(self, contest, user):
                self.contest = contest
                self.user = user

        rtimes = rounds_times(DummyRequest(self.contest, submission.user))
        round_start = rtimes[submission.problem_instance.round].get_start()
        submission_time = submission.date - round_start
        # Python2.6 does not support submission_time.total_seconds()
        return submission_time.days * 24 * 3600 + submission_time.seconds

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
                time_passed=self.get_submission_relative_time(submission)
            )
            result.score = score
            result.status = submission.status
            return submission

        else:
            result.score = None
            result.status = None
            return None

    def update_user_result_for_problem(self, result):
        submissions = Submission.objects \
                .filter(problem_instance=result.problem_instance,
                    user=result.user, kind='NORMAL') \
                .exclude(status__in=IGNORED_STATUSES) \
                .order_by('date')

        last_submission = self._fill_user_result_for_problem(
                result, submissions)
        if last_submission:
            result.submission_report = last_submission \
                    .submissionreport_set.get(status='ACTIVE', kind='FULL')

            if last_submission.status == 'OK':
                # XXX: May not ignore submissions with admin-hacked same-date
                submissions.filter(date__gt=last_submission.date) \
                        .update(status='IGN', score=None)
        else:
            result.submission_report = None

        result.save()

    def results_visible(self, request, submission):
        return False

    def get_visible_reports_kinds(self, request, submission):
        if submission.status == 'CE':
            return ['FULL']
        else:
            return []

    def can_see_submission_score(self, request, submission):
        return True

    def can_see_submission_status(self, request, submission):
        return True

    def render_submission_date(self, submission):
        return format_time(self.get_submission_relative_time(submission))

    def ranking_controller(self):
        return ACMRankingController(self.contest)

    def can_see_round(self, request, round):
        if is_contest_admin(request):
            return True
        rtimes = self.get_round_times(request, round)
        return rtimes.is_active(request.timestamp)


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

    def _rounds_for_ranking(self, request, key=CONTEST_RANKING_KEY):
        queryset = self.contest.round_set.all()
        if key != CONTEST_RANKING_KEY:
            queryset = queryset.filter(id=key)
        return queryset

    def render_ranking(self, request, key):
        data = self.serialize_ranking(request, key)
        return render_to_string('acm/acm_ranking.html',
                context_instance=RequestContext(request, data))

    def _render_ranking_csv_line(self, row):
        line = [row['place'], row['user'].first_name, row['user'].last_name]
        line += [unicode(r.score if r and r.score is not None else '')
            for r in row['results']]
        line.append(row['sum'].total_time_repr())
        return line

    def filter_users_for_ranking(self, request, key, queryset):
        return request.contest.controller.registration_controller() \
            .filter_participants(queryset)

    def _get_old_results(self, request, freeze_time, pis, users):
        controller = request.contest.controller
        submissions = Submission.objects \
                .filter(problem_instance__in=pis, user__in=users,
                     kind='NORMAL', date__lt=freeze_time) \
                .exclude(status__in=IGNORED_STATUSES) \
                .select_related('user', 'problem_instance') \
                .order_by('user', 'problem_instance', 'date')
        results = []
        for user, user_submissions in \
                itertools.groupby(submissions, attrgetter('user')):
            for pi, user_pi_submissions in itertools.groupby(user_submissions,
                    attrgetter('problem_instance')):
                result = _FakeUserResultForProblem(user, pi)
                controller._fill_user_result_for_problem(result,
                    user_pi_submissions)
                results.append(result)
        return results

    def serialize_ranking(self, request, key):
        controller = request.contest.controller
        rounds = list(self._rounds_for_ranking(request, key))
        freeze_times = [controller.get_round_freeze_time(round)
                        for round in rounds]

        pis = list(ProblemInstance.objects.filter(round__in=rounds)
                .select_related('problem').prefetch_related('round'))
        rtopis = defaultdict(lambda: [])

        for pi in pis:
            rtopis[pi.round].append(pi)

        users = self.filter_users_for_ranking(request, key, User.objects.all())

        results = []
        ccontroller = self.contest.controller

        frozen = False
        for round, freeze_time in zip(rounds, freeze_times):
            rpis = rtopis[round]
            rtimes = ccontroller.get_round_times(request, round)
            if freeze_time is None or \
                    is_contest_admin(request) or \
                    rtimes.results_visible(request.timestamp) or \
                    request.timestamp <= freeze_time:
                results += UserResultForProblem.objects \
                    .filter(problem_instance__in=rpis, user__in=users) \
                    .prefetch_related('problem_instance__round')
            else:
                results += self._get_old_results(request, freeze_time,
                                                 rpis, users)
                frozen = True

        data = self._get_users_results(pis, results, rounds, users)
        self._assign_places(data, itemgetter('sum'))
        return {'rows': data, 'problem_instances': pis, 'frozen': frozen}
