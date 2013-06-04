from django.contrib.auth.models import User
from oioioi.base.permissions import make_request_condition
from oioioi.participants.controllers import ParticipantsController
from oioioi.participants.models import Participant
from oioioi.base.utils import request_cached


def is_contest_with_participants(contest):
    rcontroller = contest.controller.registration_controller()
    return isinstance(rcontroller, ParticipantsController)


@make_request_condition
def contest_has_participants(request):
    return is_contest_with_participants(request.contest)


@request_cached
def get_participant(request):
    try:
        return Participant.objects.get(contest=request.contest,
                                       user=request.user)
    except Participant.DoesNotExist:
        return None


@make_request_condition
@request_cached
def can_register(request):
    if get_participant(request) is not None:
        return False
    rcontroller = request.contest.controller.registration_controller()
    return rcontroller.can_register(request)


@make_request_condition
@request_cached
def can_edit_registration(request):
    participant = get_participant(request)
    if participant is None:
        return False
    rcontroller = request.contest.controller.registration_controller()
    return rcontroller.can_edit_registration(request, participant)


@make_request_condition
@request_cached
def is_participant(request):
    rcontroller = request.contest.controller.registration_controller()
    qs = User.objects.filter(id=request.user.id)
    return rcontroller.filter_participants(qs).exists()
