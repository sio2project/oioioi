from django.conf import settings
from django.db.models import Q
from django.utils.translation import gettext_lazy as _

from oioioi.base.utils.query_helpers import Q_always_false
from oioioi.contests.models import Contest
from oioioi.usercontests.models import UserContest


class UserContestAuthBackend:
    description = _("User contest ownership")
    supports_authentication = False

    def authenticate(self, request, **kwargs):
        return None

    def get_owned_usercontest_ids(self, user_obj):
        if not hasattr(user_obj, "_usercontest_perms_cache"):
            user_obj._usercontest_perms_cache = set(UserContest.objects.filter(user=user_obj).values_list("contest", flat=True))
        return user_obj._usercontest_perms_cache

    def filter_for_perm(self, obj_class, perm, user):
        """Provides a :class:`django.db.models.Q` expression which can be used
        to filter `obj_class` queryset for objects `o` such that
        `has_perm(user, perm, o)` is True.
        """
        if not user.is_authenticated or not user.is_active:
            return Q_always_false()
        if obj_class is Contest:
            if (not settings.ARCHIVE_USERCONTESTS and perm == "contests.contest_basicadmin") or (
                settings.ARCHIVE_USERCONTESTS and perm == "contests.contest_observer"
            ):
                return Q(id__in=self.get_owned_usercontest_ids(user))
                # The above query avoids somewhat costly joins in favour of subqueries,
                # as opposed to the one below. The subquery will be eliminated by django
                # anyway for users who don't own usercontests.
                # return Q(usercontest__user=user)
        return Q_always_false()

    def has_perm(self, user_obj, perm, obj=None):
        if not user_obj.is_authenticated or not user_obj.is_active or not isinstance(obj, Contest):
            return False
        if (not settings.ARCHIVE_USERCONTESTS and perm == "contests.contest_basicadmin") or (
            settings.ARCHIVE_USERCONTESTS and perm == "contests.contest_observer"
        ):
            return obj.id in self.get_owned_usercontest_ids(user_obj)
        return False
