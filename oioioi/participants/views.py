from django.shortcuts import get_object_or_404, redirect
from django.core.urlresolvers import reverse
from django.utils.translation import ugettext_lazy as _
from django.template.response import TemplateResponse
from oioioi.base.menu import account_menu_registry
from oioioi.base.permissions import enforce_condition
from oioioi.contests.utils import contest_exists
from oioioi.participants.models import Participant
from oioioi.participants.utils import can_register, can_edit_registration, \
    contest_has_participants

account_menu_registry.register('participants_registration',
        _("Register to the contest"),
        lambda request: reverse(registration_view,
            kwargs={'contest_id': request.contest.id}),
        condition=contest_exists & contest_has_participants & can_register,
        order=80)

account_menu_registry.register('participants_edit_registration',
        _("Edit contest registration"),
        lambda request: reverse(registration_view,
            kwargs={'contest_id': request.contest.id}),
        condition=contest_exists & contest_has_participants
            & can_edit_registration,
        order=80)


@enforce_condition(contest_exists & contest_has_participants)
def registration_view(request, contest_id):
    rcontroller = request.contest.controller.registration_controller()
    return rcontroller.registration_view(request)


@enforce_condition(contest_exists & contest_has_participants
                   & can_edit_registration)
def unregistration_view(request, contest_id):
    if request.method == 'POST':
        participant = get_object_or_404(Participant, contest=request.contest,
                user=request.user)
        participant.delete()
        return redirect('index')
    return TemplateResponse(request, 'participants/unregister.html')
