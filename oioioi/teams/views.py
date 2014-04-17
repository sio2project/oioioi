from django.http import HttpResponseRedirect
from django.core.urlresolvers import reverse
from django.utils.translation import ugettext_lazy as _
from django.template.response import TemplateResponse
from django.shortcuts import get_object_or_404

from oioioi.base.permissions import enforce_condition, not_anonymous
from oioioi.base.menu import menu_registry
from oioioi.contests.utils import can_enter_contest, contest_exists
from oioioi.teams.models import Team, TeamMembership
from oioioi.teams.forms import CreateTeamForm
from oioioi.teams.utils import can_create_team, can_join_team, can_quit_team, \
                               can_delete_team, has_team, teams_enabled


def create_team(login, name, contest):
    new_team = Team(name=name, contest=contest, login=login)
    new_team.save()
    return new_team


def team_members_names(team):
    return [team.contest.controller.get_user_public_name(membership.user)
           for membership in team.members.all()]


@menu_registry.register_decorator(_("Team"), lambda request:
        reverse('team_view', kwargs={'contest_id': request.contest.id}),
    order=50)
@enforce_condition(not_anonymous & contest_exists & can_enter_contest &
                   teams_enabled & (has_team | can_create_team))
def team_view(request, contest_id):
    controller = request.contest.controller
    try:
        tm = TeamMembership.objects.get(user=request.user,
                                        team__contest=request.contest)
        members = team_members_names(tm.team)
        can_invite = (len(members) < controller.max_size_of_team()) and \
                controller.can_modify_team(request)
        join_link = request.build_absolute_uri(reverse('join_team',
            kwargs={'contest_id': contest_id, 'join_key': tm.team.join_key}))
        return TemplateResponse(request, 'teams/team.html',
             {'members': members, 'name': tm.team.name, 'join_link': join_link,
              'show_delete': can_delete_team(request),
              'show_quit': can_quit_team(request),
              'show_invite': can_invite})
    except TeamMembership.DoesNotExist:
        return HttpResponseRedirect(reverse('create_team',
                                   kwargs={'contest_id': request.contest.id}))


@enforce_condition(not_anonymous & contest_exists &
                   can_enter_contest & can_create_team)
def create_team_view(request, contest_id):
    if request.method == 'POST':
        team_create_form = CreateTeamForm(request.POST, request=request)
        if team_create_form.is_valid():
            new_team = create_team(team_create_form.cleaned_data['login'],
                                   team_create_form.cleaned_data['name'],
                                   request.contest)
            membership = TeamMembership(team=new_team, user=request.user)
            membership.save()
            return HttpResponseRedirect(reverse('team_view',
                     kwargs={'contest_id': request.contest.id}))
    else:
        team_create_form = CreateTeamForm()
    return TemplateResponse(request, 'teams/create_team.html',
                                {'form': team_create_form})


@enforce_condition(not_anonymous & contest_exists &
                   can_enter_contest & can_join_team)
def join_team_view(request, contest_id, join_key):
    team = get_object_or_404(Team, contest=request.contest, join_key=join_key)
    if request.method == 'POST':
        members = [membership.user for membership in
                   TeamMembership.objects.filter(team=team)]
        tm = TeamMembership(team=team, user=request.user)
        tm.save()
        return HttpResponseRedirect(reverse('team_view',
                                   kwargs={'contest_id': request.contest.id}))
    else:
        members = team_members_names(team)
        return TemplateResponse(request, 'teams/confirm_join_team.html',
                                {'join_key': join_key, 'members': members,
                                 'name': team.name})


@enforce_condition(not_anonymous & contest_exists &
                   can_enter_contest & can_delete_team)
def delete_team_view(request, contest_id):
    tm = get_object_or_404(TeamMembership, user=request.user,
                           team__contest=request.contest)
    team = tm.team
    user = team.user
    tm.delete()
    team.delete()
    user.delete()
    return HttpResponseRedirect(reverse('team_view',
                                   kwargs={'contest_id': request.contest.id}))


@enforce_condition(not_anonymous & contest_exists &
                   can_enter_contest & can_quit_team)
def quit_team_view(request, contest_id):
    tm = get_object_or_404(TeamMembership, user=request.user,
                           team__contest=request.contest)
    tm.delete()
    return HttpResponseRedirect(reverse('team_view',
                                   kwargs={'contest_id': request.contest.id}))
