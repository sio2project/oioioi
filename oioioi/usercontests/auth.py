from django.conf import settings
from django.utils.translation import ugettext_lazy as _

from oioioi.contests.models import Contest
from oioioi.usercontests.models import UserContest


class UserContestAuthBackend(object):
    description = _("User contest ownership")
    supports_authentication = False

    def authenticate(self, **kwargs):
        return None

    def has_perm(self, user_obj, perm, obj=None):
        if not user_obj.is_authenticated or not user_obj.is_active \
                or not isinstance(obj, Contest):
            return False
        if (not settings.ARCHIVE_USERCONTESTS \
                and perm == 'contests.contest_basicadmin') \
        or (settings.ARCHIVE_USERCONTESTS \
                and perm == 'contests.contest_observer'):
            if not hasattr(user_obj, '_usercontest_perms_cache'):
                user_obj._usercontest_perms_cache = set(UserContest.objects
                    .filter(user=user_obj).values_list('contest', flat=True))
            return obj.id in user_obj._usercontest_perms_cache
        return False
