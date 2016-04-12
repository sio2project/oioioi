from oioioi.base import admin
from oioioi.base.forms import AlwaysChangedModelForm
from oioioi.ipauthsync.models import IpAuthSyncConfig


class IpAuthSyncConfigInline(admin.TabularInline):
    model = IpAuthSyncConfig
    extra = 0
    form = AlwaysChangedModelForm

    def has_add_permission(self, request):
        return request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser


class ContestAdminWithIpAuthSyncInlineMixin(object):
    def __init__(self, *args, **kwargs):
        super(ContestAdminWithIpAuthSyncInlineMixin, self) \
            .__init__(*args, **kwargs)
        self.inlines = self.inlines + [IpAuthSyncConfigInline]
