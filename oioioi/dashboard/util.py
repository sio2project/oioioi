from oioioi.base.utils.public_message import get_public_message
from oioioi.dashboard.models import DashboardMessage


def get_dashboard_message(request):
    return get_public_message(
        request,
        DashboardMessage,
        'dashboard_message',
    )
