from django.template.loader import render_to_string
from django.template import RequestContext
from django.contrib.auth.models import User

from oioioi.base.utils import jsonify, allow_cross_origin
from oioioi.pa.controllers import PARegistrationController
from oioioi.dashboard.registry import dashboard_headers_registry
from oioioi.participants.utils import is_participant
from oioioi.contests.utils import is_contest_admin


@dashboard_headers_registry.register_decorator(order=10)
def registration_notice_fragment(request):
    rc = request.contest.controller.registration_controller()
    if isinstance(rc, PARegistrationController) \
            and request.user.is_authenticated() \
            and not is_contest_admin(request) \
            and not is_participant(request) \
            and rc.can_register(request):
        return render_to_string('pa/registration_notice.html',
            context_instance=RequestContext(request))
    else:
        return None


@allow_cross_origin
@jsonify
def contest_info_view(request):
    rc = request.contest.controller.registration_controller()
    users = rc.filter_participants(User.objects.all())
    return {
        'users_count': len(users),
    }
