from django.core.exceptions import SuspiciousOperation
from django.shortcuts import get_object_or_404
from django.template.response import TemplateResponse

from oioioi.base.permissions import enforce_condition
from oioioi.contests.models import Contest, Round
from oioioi.contests.utils import contest_exists
from oioioi.livedata.utils import can_see_livedata


def _ranking_settings(contest, round_id):
    round = get_object_or_404(Round, id=round_id)
    if round.contest != contest:
        raise SuspiciousOperation
    return {
        'contest': contest,
        'round': round,
        'bomb_penalty': contest.controller.get_penalty_time(),
        'freeze_time': 60 * 60 * 4,
        'round_length': 60 * 60 * 5,
        'max_refresh_rate': 1000,
    }


DEFAULT_ROUND = 126


@enforce_condition(contest_exists & can_see_livedata)
def liveranking_auto_view(request, round_id=None):
    if not round_id:
        round_id = DEFAULT_ROUND

    ranking_variables = _ranking_settings(request.contest, round_id)
    return TemplateResponse(request, 'liveranking/auto.html', ranking_variables)


@enforce_condition(contest_exists & can_see_livedata)
def liveranking_simple_view(request, round_id=None):
    if not round_id:
        round_id = DEFAULT_ROUND

    ranking_variables = _ranking_settings(request.contest, round_id)
    return TemplateResponse(request, 'liveranking/simple.html', ranking_variables)


@enforce_condition(contest_exists & can_see_livedata)
def liveranking_autoDonuts_view(request, round_id=None):
    if not round_id:
        round_id = DEFAULT_ROUND

    ranking_variables = _ranking_settings(request.contest, round_id)
    return TemplateResponse(request, 'liveranking/autoDonuts.html', ranking_variables)


@enforce_condition(contest_exists & can_see_livedata)
def liveranking_simpleDonuts_view(request, round_id=None):
    if not round_id:
        round_id = DEFAULT_ROUND

    ranking_variables = _ranking_settings(request.contest, round_id)
    return TemplateResponse(request, 'liveranking/simpleDonuts.html', ranking_variables)
