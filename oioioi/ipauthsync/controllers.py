from oioioi.contests.controllers import ContestController
from oioioi.participants.controllers import OnsiteRegistrationController
from oioioi.participants.utils import is_onsite_contest


class IpAuthSyncControllerMixin:
    """ContestController mixin that sets up the ipauthsync app."""

    def mixins_for_admin(self):
        from oioioi.ipauthsync.admin import ContestAdminWithIpAuthSyncInlineMixin

        mixins = super().mixins_for_admin()
        if is_onsite_contest(self.contest):
            mixins = mixins + (ContestAdminWithIpAuthSyncInlineMixin,)
        return mixins


ContestController.mix_in(IpAuthSyncControllerMixin)


class IpAuthSyncRegistrationControllerMixin:
    """RegistrationController mixin that adds a functionality to validate IP
    address.
    """

    def ipauthsync_validate_ip(self, region, ip, user):
        """Validates IP reported by a region server.

        Should raise an exception if the returned IP does not look like
        a correct IP address from the given region.
        """
        pass


OnsiteRegistrationController.mix_in(IpAuthSyncRegistrationControllerMixin)
