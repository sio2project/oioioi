from django.contrib.auth.models import User

from oioioi.participants.models import Participant
from oioioi.usergroups.models import UserGroup


# If the requested usergroup does not exist then we return false.
def is_usergroup_owner(user, usergroup_id):
    return UserGroup.objects.filter(id=usergroup_id).\
        filter(owners__in=[user]).exists()


def is_usergroup_attached(contest, usergroup):
    return contest in usergroup.contests.all()


def get_attached_usergroups(contest, queryset=None):
    if queryset is None:
        return contest.usergroups.all()
    return queryset.filter(contests__id=contest)


def get_owned_usergroups(user, queryset=None):
    if queryset is None:
        return user.owned_usergroups.all()
    return queryset.filter(owners__id=user)


def filter_usergroup_exclusive_members(contest, usergroup, queryset=None):
    if queryset is None:
        group_users = usergroup.members.all()
    else:
        group_users = queryset.filter(usergroups__id=usergroup.id)
    other_groups = contest.usergroups.exclude(id=usergroup.id)
    return group_users.exclude(usergroups__in=other_groups)\
        .exclude(participant__contest__id=contest.id)


def add_usergroup_to_members(contest, usergroup, only_exclusive=True):
    users = usergroup.members
    if only_exclusive:
        users = filter_usergroup_exclusive_members(contest, usergroup, users)
    users = users.exclude(participant__contest__id=contest.id)
    Participant.objects.bulk_create(
        [Participant(contest=contest, user=u) for u in users])


def move_members_to_usergroup(contest, usergroup):
    users = User.objects.filter(participant__contest__id=contest.id)
    usergroup.members.add(*list(users))
    Participant.objects.filter(contest=contest, user__in=users).delete()
