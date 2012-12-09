from django.shortcuts import get_object_or_404, redirect
from django.core.exceptions import SuspiciousOperation
from django.core.urlresolvers import reverse
from django.http import HttpResponseForbidden
from django.utils.translation import ugettext_lazy as _
from django.template.response import TemplateResponse
from oioioi.base.menu import account_menu_registry
from oioioi.participants.models import Participant
from oioioi.participants.controllers import ParticipantsController
from oioioi.participants.utils import can_register, can_edit_registration

account_menu_registry.register('participants_registration',
        _("Register to the contest"),
        lambda request: reverse(registration_view,
            kwargs={'contest_id': request.contest.id}),
        condition=can_register,
        order=80)

account_menu_registry.register('participants_edit_registration',
        _("Edit contest registration"),
        lambda request: reverse(registration_view,
            kwargs={'contest_id': request.contest.id}),
        condition=can_edit_registration,
        order=80)

def registration_view(request, contest_id):
    rcontroller = request.contest.controller.registration_controller()
    if not isinstance(rcontroller, ParticipantsController):
        raise SuspiciousOperation
    return rcontroller.registration_view(request)

def unregistration_view(request, contest_id):
    rcontroller = request.contest.controller.registration_controller()
    if request.method == 'POST':
        participant = get_object_or_404(Participant, contest=request.contest,
                user=request.user)
        if not rcontroller.can_edit_registration(request, participant):
            return HttpResponseForbidden()
        participant.delete()
        return redirect('index')
    return TemplateResponse(request, 'participants/unregister.html')
