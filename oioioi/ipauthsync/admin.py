from oioioi.base import admin
from oioioi.base.forms import AlwaysChangedModelForm
from oioioi.ipauthsync.models import IpAuthSyncConfig
from django.utils.translation import gettext_lazy as _


class IpAuthSyncConfigInline(admin.TabularInline):
    model = IpAuthSyncConfig
    extra = 0
    form = AlwaysChangedModelForm
    category = _("Advanced")

    def has_add_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser


class ContestAdminWithIpAuthSyncInlineMixin(object):
    """Adds :class:`~oioioi.ipauthsync.models.IpAuthSyncConfig` to an admin
    panel.
    """

    def __init__(self, *args, **kwargs):
        super(ContestAdminWithIpAuthSyncInlineMixin, self).__init__(*args, **kwargs)
        self.inlines = tuple(self.inlines) + (IpAuthSyncConfigInline,)
