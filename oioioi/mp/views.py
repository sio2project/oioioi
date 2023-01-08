from django.template.loader import render_to_string

from oioioi.contests.utils import is_contest_admin
from oioioi.dashboard.registry import dashboard_headers_registry
from oioioi.mp.controllers import MPRegistrationController
from oioioi.participants.utils import is_participant


@dashboard_headers_registry.register_decorator(order=10)
def registration_notice_fragment(request):
    rc = request.contest.controller.registration_controller()
    if (
        isinstance(rc, MPRegistrationController)
        and request.user.is_authenticated
        and not is_contest_admin(request)
        and not is_participant(request)
        and rc.can_register(request)
    ):
        return render_to_string('mp/registration-notice.html', request=request)
    else:
        return None
