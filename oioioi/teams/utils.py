from oioioi.base.permissions import make_request_condition
from oioioi.teams.models import TeamMembership, TeamsConfig


@make_request_condition
def teams_enabled(request):
    try:
        return request.contest.teamsconfig.enabled
    except TeamsConfig.DoesNotExist:
        return False


def team_members_count(request):
    """Returns a number of members in the team for the user and the contest
       from the request.
       If user does not belong to any team the function will return 0.
    """
    tms = TeamMembership.objects.filter(user=request.user,
                                       team__contest=request.contest)
    if not tms.exists():
        return 0
    return tms[0].team.members.count()


@make_request_condition
def can_join_team(request):
    return team_members_count(request) == 0 and \
           request.contest.controller.can_modify_team(request)


@make_request_condition
def can_quit_team(request):
    return team_members_count(request) > 1 and \
           request.contest.controller.can_modify_team(request)


@make_request_condition
def can_delete_team(request):
    return team_members_count(request) == 1 and \
           request.contest.controller.can_modify_team(request)


@make_request_condition
def can_create_team(request):
    return team_members_count(request) == 0 and \
           request.contest.controller.can_modify_team(request)


@make_request_condition
def has_team(request):
    return team_members_count(request) != 0
