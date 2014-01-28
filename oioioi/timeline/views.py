from django.utils.translation import ugettext_lazy as _
from django.core.urlresolvers import reverse
from django.template.response import TemplateResponse

from oioioi.base.permissions import enforce_condition
from oioioi.contests.menu import contest_admin_menu_registry
from oioioi.contests.utils import is_contest_admin, contest_exists
from oioioi.contests.date_registration import date_registry


@contest_admin_menu_registry.register_decorator(_("Timeline"), lambda request:
        reverse('timeline_view'))
@enforce_condition(contest_exists & is_contest_admin)
def timeline_view(request):
    return TemplateResponse(request, 'timeline/timeline_view.html',
                {'registry' : date_registry.tolist(request.contest.id)})
