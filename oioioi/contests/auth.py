from django.utils.translation import ugettext_lazy as _
from oioioi.contests.models import ContestPermission, Contest


class ContestPermissionsAuthBackend(object):
    description = _("Contests permissions")
    supports_authentication = False

    def authenticate(self, **kwargs):
        return None

    def has_perm(self, user_obj, perm, obj=None):
        if not user_obj.is_authenticated() or not user_obj.is_active:
            return False
        if obj is None or not isinstance(obj, Contest):
            return False
        return ContestPermission.objects.filter(user=user_obj, contest=obj,
            permission=perm).exists()
