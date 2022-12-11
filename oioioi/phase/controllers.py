from django.utils.translation import ugettext_lazy as _

from oioioi.contests.models import Submission, SubmissionReport
from oioioi.contests.scores import IntegerScore
from oioioi.participants.controllers import ParticipantsController
from oioioi.contests.utils import is_contest_admin
from oioioi.phase.models import Phase
from oioioi.programs.controllers import ProgrammingContestController


class _FirstPhase:
    multiplier = 100


class PhaseOpenContestController(ProgrammingContestController):
    description = _("Phase open contest")

    def fill_evaluation_environ(self, environ, submission):
        super(PhaseOpenContestController, self) \
            .fill_evaluation_environ(environ, submission)

        environ['group_scorer'] = 'oioioi.programs.utils.min_group_scorer'
        environ['test_scorer'] = \
            'oioioi.programs.utils.threshold_linear_test_scorer'
    
    def can_see_test_comments(self, request, submissionreport):
        return is_contest_admin(request)

    def update_user_result_for_problem(self, result):
        try:
            submissions = Submission.objects \
                .filter(problem_instance=result.problem_instance) \
                .filter(user=result.user) \
                .filter(score__isnull=False) \
                .exclude(status='CE') \
                .filter(kind='NORMAL') \
                .order_by('date')

            round = result.problem_instance.round

            phases = list(Phase.objects
                          .filter(round=round)
                          .order_by('start_date'))
            phases.insert(0, _FirstPhase())

            next_phase_index = 1
            subs_by_phase = [[]]
            for s in submissions:
                while (next_phase_index < len(phases) and
                               phases[next_phase_index].start_date <= s.date):
                    cur_phase = phases[next_phase_index]
                    subs_by_phase.append([])
                    next_phase_index = next_phase_index + 1
                subs_by_phase[-1].append(s)

            lastHighest = 0
            total = 0
            for subs, phase in zip(subs_by_phase, phases):
                if subs:
                    phase_score = subs[-1].score.to_int()
                    if phase_score > lastHighest:
                        total += (phase_score - lastHighest) * phase.multiplier
                        lastHighest = phase_score

            chosen_submission = submissions.latest()  # mostly to link it later

            try:
                report = SubmissionReport.objects.get(
                    submission=chosen_submission, status='ACTIVE',
                    kind='NORMAL')
            except SubmissionReport.DoesNotExist:
                report = None

            result.score = IntegerScore(total // 100)
            result.status = chosen_submission.status
            result.submission_report = report
        except Submission.DoesNotExist:
            result.score = None
            result.status = None
            result.submission_report = None


class PhaseContestController(PhaseOpenContestController):
    description = _("Phase contest")

    def registration_controller(self):
        return ParticipantsController(self.contest)
