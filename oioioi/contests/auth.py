from django.db.models import Q
from django.utils.translation import gettext_lazy as _

from oioioi.base.utils.query_helpers import (
    Q_always_false,
    Q_always_true,
)
from oioioi.contests.models import Contest, ContestPermission


class ContestPermissionsAuthBackend(object):
    description = _("Contests permissions")
    supports_authentication = False

    def authenticate(self, request, **kwargs):
        return None

    def filter_for_perm(self, obj_class, perm, user):
        """Provides a :class:`django.db.models.Q` expression which can be used
        to filter `obj_class` queryset for objects `o` such that
        `has_perm(user, perm, o)` is True.
        """
        if not user.is_authenticated or not user.is_active:
            return Q_always_false()
        if obj_class is Contest:
            if user.is_superuser:
                return Q_always_true()
            query = Q(contestpermission__permission=perm, contestpermission__user=user)
            if perm == 'contests.contest_admin':
                query |= self.filter_for_perm(obj_class, 'contests.contest_owner', user)
            if perm == 'contests.contest_basicadmin':
                query |= self.filter_for_perm(obj_class, 'contests.contest_admin', user)
            return query
        return Q_always_false()

    def has_perm(self, user_obj, perm, obj=None):
        if not user_obj.is_authenticated or not user_obj.is_active:
            return False
        if obj is None or not isinstance(obj, Contest):
            return False
        if perm == 'contests.contest_admin' and self.has_perm(
            user_obj, 'contests.contest_owner', obj
        ):
            return True
        if perm == 'contests.contest_basicadmin' and self.has_perm(
            user_obj, 'contests.contest_admin', obj
        ):
            return True
        if not hasattr(user_obj, '_contest_perms_cache'):
            user_obj._contest_perms_cache = set(
                ContestPermission.objects.filter(user=user_obj).values_list(
                    'contest', 'permission'
                )
            )
        return (obj.id, perm) in user_obj._contest_perms_cache
