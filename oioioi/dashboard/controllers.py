from django.core.urlresolvers import reverse
from oioioi.contests.controllers import ContestController

class DashboardDefaultViewMixin(object):
    def default_view(self, request):
        if request.user.is_authenticated():
            return reverse('contest_dashboard',
                    kwargs={'contest_id': self.contest.id})
        else:
            return super(DashboardDefaultViewMixin, self).default_view(request)
ContestController.mix_in(DashboardDefaultViewMixin)
