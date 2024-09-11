from oioioi.base.permissions import make_request_condition
from oioioi.welcomepage.models import WelcomePageMessage


@make_request_condition
def any_welcome_messages(request):
    return WelcomePageMessage.objects.exists()
