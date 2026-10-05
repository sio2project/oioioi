from oioioi.base.forms import PublicMessageForm
from oioioi.dashboard.models import DashboardMessage


class DashboardMessageForm(PublicMessageForm):
    class Meta:
        model = DashboardMessage
        fields = ["content"]
