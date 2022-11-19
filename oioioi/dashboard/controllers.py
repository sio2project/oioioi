from django.urls import reverse

from oioioi.contests.controllers import ContestController
from oioioi.contests.utils import can_enter_contest


class DashboardDefaultViewMixin(object):
    """ContestController mixin that sets contest dashboard as a default
    contest view.
    """

    def default_view(self, request):
        if request.contest and can_enter_contest(request):
            return reverse('contest_dashboard', kwargs={'contest_id': self.contest.id})
        else:
            return super(DashboardDefaultViewMixin, self).default_view(request)


ContestController.mix_in(DashboardDefaultViewMixin)
