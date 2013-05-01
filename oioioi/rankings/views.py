from django.http import Http404
from django.template.response import TemplateResponse
from django.core.urlresolvers import reverse
from django.utils.translation import ugettext_lazy as _
from oioioi.base.permissions import enforce_condition, make_request_condition
from oioioi.base.menu import menu_registry
from oioioi.contests.utils import can_enter_contest, is_contest_admin, \
    contest_exists


@make_request_condition
def has_any_ranking_visible(request):
    rcontroller = request.contest.controller.ranking_controller()
    return bool(rcontroller.available_rankings(request))

@menu_registry.register_decorator(_("Ranking"), lambda request:
        reverse('default_ranking', kwargs={'contest_id': request.contest.id}),
    order=440)
@enforce_condition(contest_exists & can_enter_contest)
@enforce_condition(has_any_ranking_visible,
                   template='rankings/no_rankings.html')
def ranking_view(request, contest_id, key=None):
    rcontroller = request.contest.controller.ranking_controller()
    choices = rcontroller.available_rankings(request)
    if key is None:
        key = choices[0][0]
    if key not in zip(*choices)[0]:
        raise Http404
    ranking = rcontroller.render_ranking(request, key)
    return TemplateResponse(request, 'rankings/ranking_view.html',
                {'choices': choices, 'ranking': ranking, 'key': key})

@enforce_condition(contest_exists & is_contest_admin)
def ranking_csv_view(request, contest_id, key):
    rcontroller = request.contest.controller.ranking_controller()
    choices = rcontroller.available_rankings(request)
    if not choices or key not in zip(*choices)[0]:
        raise Http404

    return rcontroller.render_ranking_to_csv(request, key)
