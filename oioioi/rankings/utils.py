from oioioi.base.utils.public_message import get_public_message
from oioioi.rankings.models import RankingMessage


def get_ranking_message(request):
    return get_public_message(
        request,
        RankingMessage,
        'ranking_message',
    )
