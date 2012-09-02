from django.shortcuts import get_object_or_404
from django.http import Http404
from django.template import RequestContext
from django.template.response import TemplateResponse
from django.core.urlresolvers import reverse
from django.utils.translation import ugettext_lazy as _
from oioioi.base.menu import menu_registry
from oioioi.contests.utils import enter_contest_permission_required

# This adds the required mixin to the ContestController class
import oioioi.rankings.controllers

def any_ranking_visible(request):
    rcontroller = request.contest.controller.ranking_controller()
    return bool(rcontroller.available_rankings(request))

menu_registry.register('ranking', _("Ranking"),
        lambda request: reverse('default_ranking', kwargs={'contest_id':
            request.contest.id}), condition=any_ranking_visible,
        order=440)

@enter_contest_permission_required
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
