from django.db.models import Q
from django.utils import timezone

from oioioi.rankings.controllers import CONTEST_RANKING_KEY
from oioioi.teachers.controllers import TeacherRegistrationController
from oioioi.usergroups.models import UserGroup, UserGroupRanking
from oioioi.contests.utils import is_contest_basicadmin, is_contest_observer
from oioioi.rankings.controllers import DefaultRankingController
from oioioi.rankings.models import Ranking

USER_GROUP_RANKING_PREFIX = 'g'


class UserGroupsParticipantsControllerMixin(object):
    def filter_participants(self, queryset):
        base_qs = super(
            UserGroupsParticipantsControllerMixin, self
        ).filter_participants(queryset)
        groups_qs = queryset.filter(usergroups__contests__id=self.contest.id)
        return base_qs | groups_qs

    def user_contests_query(self, request):
        base_query = super(
            UserGroupsParticipantsControllerMixin, self
        ).user_contests_query(request)
        if not request.user.is_authenticated:
            return base_query
        return base_query | Q(usergroups__members__id=request.user.id)


TeacherRegistrationController.mix_in(UserGroupsParticipantsControllerMixin)


def user_group_ranking_id(user_group_id):
    return USER_GROUP_RANKING_PREFIX + str(user_group_id)


class UserGroupsDefaultRankingControllerMixin(object):
    def _iter_user_groups(self, can_see_all, request):
        queryset = UserGroupRanking.objects.filter(contest__id=self.contest.id)

        for user_group_ranking in queryset:
            user_group = user_group_ranking.user_group
            if can_see_all or (request and request.user in user_group.members.all()):
                yield user_group

    def _user_groups_for_ranking(self, request):
        can_see_all = is_contest_basicadmin(request) or is_contest_observer(request)
        return self._iter_user_groups(can_see_all, request)

    def _rounds_for_key(self, key):
        can_see_all = self._key_permission(key) in {'admin', 'observer'}
        partial_key = self.get_partial_key(key)
        # Get all visible rounds for user group rankings.
        if partial_key[0] == USER_GROUP_RANKING_PREFIX:
            partial_key = CONTEST_RANKING_KEY
        return self._iter_rounds(can_see_all, timezone.now(), partial_key)

    def available_rankings(self, request):
        rankings = super(
            UserGroupsDefaultRankingControllerMixin, self
        ).available_rankings(request)
        if len(rankings) == 0:
            # User cannot see any rounds.
            return []

        for user_group in self._user_groups_for_ranking(request):
            rankings.append((user_group_ranking_id(user_group.id), user_group.name))
        return rankings

    def keys_for_pi(self, pi):
        raise NotImplementedError

    def invalidate_pi(self, pi):
        Ranking.invalidate_contest(pi.contest)

    def filter_users_for_ranking(self, key, queryset):
        queryset = super(
            UserGroupsDefaultRankingControllerMixin, self
        ).filter_users_for_ranking(key, queryset)
        partial_key = self.get_partial_key(key)

        if partial_key[0] == USER_GROUP_RANKING_PREFIX:
            user_group = UserGroup.objects.get(id=int(partial_key[1:]))
            users = user_group.members.all()
            queryset = queryset & users
        return queryset


DefaultRankingController.mix_in(UserGroupsDefaultRankingControllerMixin)
