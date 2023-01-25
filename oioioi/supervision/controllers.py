from django.db.models import Q

from oioioi.supervision.utils import can_user_enter_round
from oioioi.contests.controllers import ContestController,RegistrationController

class SupervisionMixinForContestController(object):
    def can_see_round(self, request_or_context, round):
        return can_user_enter_round(request_or_context, round) and super(
                SupervisionMixinForContestController,
                self,
                ).can_see_round(request_or_context, round)

    def can_submit(self, request, problem_instance, check_round_times=True):
        return can_user_enter_round(request, problem_instance.round) and super(
                    SupervisionMixinForContestController,
                    self,
                ).can_submit(
                    request,
                    problem_instance,
                    check_round_times,
                )

ContestController.mix_in(SupervisionMixinForContestController)

class SupervisionMixinForRegistrationControllers(object):
    # can_enter_contest uses filter_visible_contests
    # and that uses the following method...
    # ... at least in ContestController. Don't know about others.
    def visible_contests_query(self, request):
        filt = super(
                SupervisionMixinForRegistrationControllers,
                self,
                ).visible_contests_query(request)
        if request.is_under_supervision and not request.user.is_superuser:
            filt &= Q(id__in=request.supervised_contests)
        return filt

# See notes in PublicContestRegistrationController. If a class MUST
# override visible_contests_query, it needs this mixin or a substitute.
RegistrationController.mix_in(SupervisionMixinForRegistrationControllers)
