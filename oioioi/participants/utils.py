from django.core.exceptions import SuspiciousOperation
from django.contrib.auth.models import User
from oioioi.participants.controllers import ParticipantsController
from oioioi.participants.models import Participant
from oioioi.base.utils import request_cached

@request_cached
def can_register(request):
    rcontroller = request.contest.controller.registration_controller()
    if not isinstance(rcontroller, ParticipantsController):
        return False
    if Participant.objects.filter(contest=request.contest,
            user=request.user):
        return False
    return rcontroller.can_register(request)

@request_cached
def can_edit_registration(request):
    rcontroller = request.contest.controller.registration_controller()
    if not isinstance(rcontroller, ParticipantsController):
        return False
    try:
        participant = Participant.objects.get(contest=request.contest,
            user=request.user)
    except Participant.DoesNotExist:
        return False
    return rcontroller.can_edit_registration(request, participant)

@request_cached
def is_participant(request):
    rcontroller = request.contest.controller.registration_controller()
    qs = User.objects.filter(id=request.user.id)
    return rcontroller.filter_participants(qs).exists()

