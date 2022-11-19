from django.shortcuts import get_object_or_404, redirect
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from oioioi.base.menu import account_menu_registry
from oioioi.base.permissions import enforce_condition, not_anonymous
from oioioi.contests.menu import (
    contest_admin_menu_registry,
    personal_data_menu_registry,
)
from oioioi.contests.utils import (
    can_see_personal_data,
    contest_exists,
    is_contest_admin,
)
from oioioi.participants.models import Participant
from oioioi.participants.utils import (
    can_edit_registration,
    can_register,
    can_unregister,
    contest_has_participants,
    render_participants_data_csv,
    serialize_participants_data,
)

account_menu_registry.register(
    'participants_registration',
    _("Register to the contest"),
    lambda request: reverse(
        'participants_register', kwargs={'contest_id': request.contest.id}
    ),
    condition=contest_exists & contest_has_participants & can_register,
    order=80,
)

account_menu_registry.register(
    'participants_edit_registration',
    _("Edit contest registration"),
    lambda request: reverse(
        'participants_register', kwargs={'contest_id': request.contest.id}
    ),
    condition=contest_exists & contest_has_participants & can_edit_registration,
    order=80,
)


@enforce_condition(not_anonymous & contest_exists & contest_has_participants)
def registration_view(request):
    rcontroller = request.contest.controller.registration_controller()
    return rcontroller.registration_view(request)


@enforce_condition(
    not_anonymous & contest_exists & contest_has_participants & can_unregister
)
def unregistration_view(request):
    if request.method == 'POST':
        participant = get_object_or_404(
            Participant, contest=request.contest, user=request.user
        )
        participant.delete()
        return redirect('index')
    return TemplateResponse(request, 'participants/unregister.html')


@contest_admin_menu_registry.register_decorator(
    _("Participants' data"),
    lambda request: reverse(
        'participants_data', kwargs={'contest_id': request.contest.id}
    ),
    condition=is_contest_admin,
    order=100,
)
@personal_data_menu_registry.register_decorator(
    _("Participants' data"),
    lambda request: reverse(
        'participants_data', kwargs={'contest_id': request.contest.id}
    ),
    condition=(can_see_personal_data & ~is_contest_admin),
    order=100,
)
@enforce_condition(
    not_anonymous & contest_exists & contest_has_participants & can_see_personal_data
)
def participants_data(request):
    context = serialize_participants_data(
        request, Participant.objects.filter(contest=request.contest)
    )
    return TemplateResponse(request, 'participants/data.html', context)


@enforce_condition(
    not_anonymous & contest_exists & contest_has_participants & can_see_personal_data
)
def participants_data_csv(request):
    return render_participants_data_csv(
        request, Participant.objects.filter(contest=request.contest), request.contest.id
    )
