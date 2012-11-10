from django.core.exceptions import SuspiciousOperation
from oioioi.participants.controllers import ParticipantsController
from oioioi.participants.models import Participant

def can_register(request):
    rcontroller = request.contest.controller.registration_controller()
    if not isinstance(rcontroller, ParticipantsController):
        return False
    if Participant.objects.filter(contest=request.contest,
            user=request.user):
        return False
    return rcontroller.can_register(request)

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
