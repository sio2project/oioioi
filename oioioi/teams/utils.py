from oioioi.base.permissions import make_request_condition, not_anonymous
from oioioi.contests.utils import is_contest_admin
from oioioi.teams.models import Team, TeamMembership, TeamsConfig


@make_request_condition
def teams_enabled(request):
    try:
        return request.contest.teamsconfig.enabled
    except TeamsConfig.DoesNotExist:
        return False


@make_request_condition
def can_see_teams_list(request):
    if not hasattr(request, 'contest'):
        return False

    if not Team.objects.filter(contest=request.contest).exists():
        return False
    try:
        cfg = TeamsConfig.objects.get(contest=request.contest)
    except TeamsConfig.DoesNotExist:
        return is_contest_admin(request)
    return (
        is_contest_admin(request)
        | (cfg.teams_list_visible == 'PUBLIC')
        | ((cfg.teams_list_visible == 'YES') & not_anonymous(request))
    )


def team_members_count(request):
    """Returns a number of members in the team for the user and the contest
    from the request.
    If user does not belong to any team the function will return 0.
    """
    tms = TeamMembership.objects.filter(
        user=request.user, team__contest=request.contest
    )
    if not tms.exists():
        return 0
    return tms[0].team.members.count()


@make_request_condition
def can_join_team(request):
    return team_members_count(
        request
    ) == 0 and request.contest.controller.can_modify_team(request)


@make_request_condition
def can_quit_team(request):
    return team_members_count(
        request
    ) > 1 and request.contest.controller.can_modify_team(request)


@make_request_condition
def can_delete_team(request):
    return team_members_count(
        request
    ) == 1 and request.contest.controller.can_modify_team(request)


@make_request_condition
def can_create_team(request):
    return team_members_count(
        request
    ) == 0 and request.contest.controller.can_modify_team(request)


@make_request_condition
def has_team(request):
    return team_members_count(request) != 0
