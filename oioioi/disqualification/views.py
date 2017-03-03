from oioioi.contests.models import Submission
from oioioi.dashboard.registry import dashboard_registry

from oioioi.disqualification.controllers import \
    DisqualificationContestControllerMixin


@dashboard_registry.register_decorator(order=10)
def disqualification_fragment(request):
    if not request.user.is_authenticated():
        return None
    cc = request.contest.controller
    if not isinstance(cc, DisqualificationContestControllerMixin):
        return None

    submissions = Submission.objects \
        .filter(problem_instance__contest=request.contest) \
        .order_by('-date').select_related()
    submissions = cc.filter_my_visible_submissions(request, submissions)
    if not submissions:
        return None

    return cc.render_disqualifications(request, submissions)
