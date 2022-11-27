from django.template.loader import render_to_string
from django.conf import settings
from oioioi.contests.utils import is_contest_admin
from oioioi.participants.utils import is_participant
from oioioi.dashboard.registry import dashboard_headers_registry
from oioioi.talent.controllers import TalentRegistrationController

@dashboard_headers_registry.register_decorator(order=10)
def registration_notice_fragment(request):
    rc = request.contest.controller.registration_controller()
    if (
        isinstance(rc, TalentRegistrationController)
        and request.user.is_authenticated
        and not is_contest_admin(request)
    ):
        if settings.TALENT_REGISTRATION_CLOSED:
            return render_to_string('talent/registration_closed.html', request=request)
        if not is_participant(request):
            return render_to_string('talent/registration_notice.html', request=request)
        else:
            return render_to_string('talent/registration_editable_notice.html', request=request)
    else:
        return None
