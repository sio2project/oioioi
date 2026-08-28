from oioioi.contests.models import Round
from oioioi.contests.utils import is_contest_admin, is_contest_observer, rounds_times
from oioioi.oi.models import OIDataConfirmationSettings, OIRegistration, School
from oioioi.participants.models import Participant
from oioioi.participants.utils import is_participant


def get_schools(request):
    contest = request.contest
    if contest and hasattr(contest.controller, "get_filtered_schools"):
        return contest.controller.get_filtered_schools(request)
    return School.objects.filter(is_active=True)


def get_data_confirmation_settings(contest):
    return OIDataConfirmationSettings.objects.filter(contest=contest).first()


def get_participant_requiring_data_confirmation(request):
    from oioioi.oi.controllers import OIFinalOnsiteContestController

    if not getattr(request, "contest", None):
        return None
    if not isinstance(request.contest.controller, OIFinalOnsiteContestController):
        return None

    confirmation_settings = get_data_confirmation_settings(request.contest)
    if confirmation_settings is not None and not confirmation_settings.is_enabled:
        return None

    if not request.user.is_authenticated:
        return None
    if is_contest_admin(request) or is_contest_observer(request):
        return None
    if not is_participant(request):
        return None

    trial_rounds = Round.objects.filter(contest=request.contest, is_trial=True)
    rtimes = rounds_times(request, request.contest)
    active_trial = any(rtimes[r].is_active(request.timestamp) for r in trial_rounds if r in rtimes)
    if not active_trial:
        return None

    try:
        participant = Participant.objects.get(user=request.user, contest=request.contest)
    except Participant.DoesNotExist:
        return None

    reg = OIRegistration.objects.filter(participant=participant).first()
    if reg is not None and reg.data_confirmed_at is not None:
        return None

    return participant
