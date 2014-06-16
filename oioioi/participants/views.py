from django.shortcuts import get_object_or_404, redirect
from django.core.urlresolvers import reverse
from django.utils.translation import ugettext_lazy as _
from django.template.response import TemplateResponse
from oioioi.base.menu import account_menu_registry
from oioioi.base.permissions import enforce_condition, not_anonymous
from oioioi.contests.utils import contest_exists, can_see_personal_data, \
    is_contest_admin
from oioioi.contests.menu import contest_admin_menu_registry, \
    personal_data_menu_registry
from oioioi.participants.models import Participant
from oioioi.participants.utils import can_register, can_edit_registration, \
    contest_has_participants, can_unregister, serialize_participants_data, \
    render_participants_data_csv

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


@enforce_condition(not_anonymous & contest_exists & contest_has_participants)
def registration_view(request, contest_id):
    rcontroller = request.contest.controller.registration_controller()
    return rcontroller.registration_view(request)


@enforce_condition(not_anonymous & contest_exists & contest_has_participants
                   & can_unregister)
def unregistration_view(request, contest_id):
    if request.method == 'POST':
        participant = get_object_or_404(Participant, contest=request.contest,
                user=request.user)
        participant.delete()
        return redirect('index')
    return TemplateResponse(request, 'participants/unregister.html')


@contest_admin_menu_registry.register_decorator(_("Participants' data"),
        lambda request: reverse('participants_data',
                                kwargs={'contest_id': request.contest.id}),
        condition=is_contest_admin,
        order=100)
@personal_data_menu_registry.register_decorator(_("Participants' data"),
        lambda request: reverse('participants_data',
                                kwargs={'contest_id': request.contest.id}),
        condition=(can_see_personal_data & ~is_contest_admin),
        order=100)
@enforce_condition(not_anonymous & contest_exists & contest_has_participants &
                   can_see_personal_data)
def participants_data(request, contest_id):
    context = serialize_participants_data(
            Participant.objects.filter(contest=request.contest))
    return TemplateResponse(request, 'participants/data.html', context)


@enforce_condition(not_anonymous & contest_exists & contest_has_participants &
                   can_see_personal_data)
def participants_data_csv(request, contest_id):
    return render_participants_data_csv(
            Participant.objects.filter(contest=request.contest), contest_id)
