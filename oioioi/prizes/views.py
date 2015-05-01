from collections import namedtuple, OrderedDict
from django.conf import settings
from django.http import Http404
from django.template.response import TemplateResponse
from django.core.urlresolvers import reverse
from django.utils.translation import ugettext_lazy as _
from django.shortcuts import get_object_or_404
from oioioi.base.permissions import enforce_condition, make_request_condition
from oioioi.base.menu import menu_registry
from oioioi.contests.utils import can_enter_contest, contest_exists, \
        is_contest_admin
from oioioi.prizes.models import PrizeForUser, PrizeGiving
from oioioi.filetracker.utils import stream_file


@make_request_condition
def prizes_visible(request):
    return request.contest.controller.can_see_prizes(request)


@make_request_condition
def any_prize_awarded(request):
    return PrizeGiving.objects.filter(contest=request.contest) \
            .filter(state='SUCCESS', prize__prizeforuser__isnull=False) \
            .exists()


@menu_registry.register_decorator(_("Prizes"), lambda request:
        reverse('default_prizes', kwargs={'contest_id': request.contest.id}),
    order=990)
@enforce_condition(contest_exists & can_enter_contest)
@enforce_condition(any_prize_awarded & prizes_visible)
def prizes_view(request, key=None):
    givings = request.contest.prizegiving_set \
            .filter(state='SUCCESS', prize__prizeforuser__isnull=False) \
            .distinct()

    groups = OrderedDict()
    for id, name in givings.values_list('id', 'name'):
        groups.setdefault(name, []).append(id)

    Group = namedtuple('Group', 'name ids')
    groups = map(Group._make, groups.items())

    key = int(key) if key is not None else groups[0].ids[0]

    group = [group for group in groups if group.ids[0] == key]
    if not group:
        raise Http404
    group = group[0]

    pfus = PrizeForUser.objects.select_related('user', 'prize') \
            .filter(prize__prize_giving__in=group.ids)

    return TemplateResponse(request, 'prizes/prizes.html',
        {'groups': groups, 'key': key, 'pfus': pfus,
         'users_on_page': getattr(settings, 'PRIZES_ON_PAGE', 100)})


@enforce_condition(contest_exists & is_contest_admin)
def download_report_view(request, pg_id):
    pg = get_object_or_404(PrizeGiving, id=pg_id)
    if not pg.report:
        raise Http404
    return stream_file(pg.report, name="prizes_report.csv")
