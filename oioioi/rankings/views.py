from django.http import Http404
from django.template.response import TemplateResponse
from django.core.urlresolvers import reverse
from django.utils.translation import ugettext_lazy as _
from oioioi.base.permissions import enforce_condition
from oioioi.base.menu import menu_registry
from oioioi.contests.utils import can_enter_contest, is_contest_admin

# This adds the required mixin to the ContestController class

def any_ranking_visible(request):
    rcontroller = request.contest.controller.ranking_controller()
    return bool(rcontroller.available_rankings(request))

menu_registry.register('ranking', _("Ranking"),
        lambda request: reverse('default_ranking', kwargs={'contest_id':
            request.contest.id}), condition=any_ranking_visible,
        order=440)

@enforce_condition(can_enter_contest)
def ranking_view(request, contest_id, key=None):
    rcontroller = request.contest.controller.ranking_controller()
    choices = rcontroller.available_rankings(request)
    if not choices:
        return TemplateResponse(request, 'rankings/no_rankings.html')
    if key is None:
        key = choices[0][0]
    if key not in zip(*choices)[0]:
        raise Http404
    ranking = rcontroller.render_ranking(request, key)
    return TemplateResponse(request, 'rankings/ranking_view.html',
                {'choices': choices, 'ranking': ranking, 'key': key})

@enforce_condition(is_contest_admin)
def ranking_csv_view(request, contest_id, key):
    rcontroller = request.contest.controller.ranking_controller()
    choices = rcontroller.available_rankings(request)
    if not choices or key not in zip(*choices)[0]:
        raise Http404

    return rcontroller.render_ranking_to_csv(request, key)
