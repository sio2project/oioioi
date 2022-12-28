from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import Q

from oioioi.acm.controllers import ACMContestController
from oioioi.balloons.models import BalloonDelivery
from oioioi.contests.models import Submission


class BalloonsDeliveryACMControllerMixin(object):
    """Creates a :class:`~oioioi.balloons.models.BalloonDelivery` object for
    every submission that has been successfully judged, but only if it's
    the first judged submission for that problem instance or
    a `BalloonDelivery` object was already created for that problem
    instance.
    """

    def submission_judged(self, submission, rejudged=False):
        super(BalloonsDeliveryACMControllerMixin, self).submission_judged(
            submission, rejudged
        )
        self._create_balloon_delivery(submission)

    @transaction.atomic
    def _create_balloon_delivery(self, submission):
        this_problem_instance = Q(problem_instance=submission.problem_instance)
        if submission.user_id is None:
            return
        if BalloonDelivery.objects.filter(this_problem_instance).exists():
            # First solver has been determined, just create a request if OK.
            user_qs = User.objects.filter(id=submission.user_id)
            registration_controller = (
                submission.problem_instance.contest.controller.registration_controller()
            )
            participant_qs = registration_controller.filter_participants(user_qs)
            if (
                submission.status == 'OK'
                and submission.kind == 'NORMAL'
                and participant_qs.exists()
            ):
                BalloonDelivery.objects.get_or_create(
                    user=submission.user, problem_instance=submission.problem_instance
                )
        else:
            # First solver has not been determined yet.
            # It may be necessary to wait for some submissions to be judged.
            accepted_or_unjudged = Q(status='OK') | Q(status='?') | Q(status='SE')
            not_ignored = Q(kind='NORMAL')
            user_is_participant = Q(
                user__participant__contest=submission.problem_instance.contest_id
            )
            submissions = Submission.objects.filter(
                accepted_or_unjudged
                & this_problem_instance
                & not_ignored
                & user_is_participant
            ).order_by('date')

            first_not_found = True
            for submission in submissions:
                if submission.status in ('?', 'SE'):
                    if first_not_found:
                        # We are waiting for this submission to be judged.
                        break
                else:
                    BalloonDelivery.objects.get_or_create(
                        user=submission.user,
                        problem_instance=submission.problem_instance,
                        first_accepted_solution=first_not_found,
                    )
                    first_not_found = False


ACMContestController.mix_in(BalloonsDeliveryACMControllerMixin)
