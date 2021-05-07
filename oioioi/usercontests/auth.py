from django.conf import settings
from django.db.models import Q
from django.utils.translation import ugettext_lazy as _

from oioioi.contests.models import Contest
from oioioi.usercontests.models import UserContest


class UserContestAuthBackend(object):
    description = _("User contest ownership")
    supports_authentication = False

    def authenticate(self, request, **kwargs):
        return None

    def filter_for_perm(self, obj_class, perm, user):
        """Provides a :class:`django.db.models.Q` expression which can be used
        to filter `obj_class` queryset for objects `o` such that
        `has_perm(user, perm, o)` is True.
        """
        if not user.is_authenticated or not user.is_active:
            return Q(pk__isnull=True)  # (False)
        if obj_class is Contest:
            if (
                not settings.ARCHIVE_USERCONTESTS
                and perm == 'contests.contest_basicadmin'
            ) or (
                settings.ARCHIVE_USERCONTESTS and perm == 'contests.contest_observer'
            ):
                return Q(usercontest__user=user)
        return Q(pk__isnull=True)  # (False)

    def has_perm(self, user_obj, perm, obj=None):
        if (
            not user_obj.is_authenticated
            or not user_obj.is_active
            or not isinstance(obj, Contest)
        ):
            return False
        if (
            not settings.ARCHIVE_USERCONTESTS and perm == 'contests.contest_basicadmin'
        ) or (settings.ARCHIVE_USERCONTESTS and perm == 'contests.contest_observer'):
            if not hasattr(user_obj, '_usercontest_perms_cache'):
                user_obj._usercontest_perms_cache = set(
                    UserContest.objects.filter(user=user_obj).values_list(
                        'contest', flat=True
                    )
                )
            return obj.id in user_obj._usercontest_perms_cache
        return False
