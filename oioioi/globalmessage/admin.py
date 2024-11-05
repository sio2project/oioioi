from django.forms import ModelForm
from django.http import HttpRequest
from django.urls import re_path, reverse
from django.utils.translation import gettext_lazy as _

from oioioi.base import admin
from oioioi.base.permissions import is_superuser
from oioioi.globalmessage.models import GlobalMessage

class GlobalMessageAdmin(admin.ModelAdmin):
    fieldsets = [
        (None, {'fields': ['enabled', 'message']}),
        (_("Auto show and hide"), {'fields': ['start', 'end']}),
    ]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return False

    def get_urls(self):
        # Global Message singleton always has primary_key = 1
        # @see GlobalMessage.get_singleton
        pk = '1'
        urls = super(GlobalMessageAdmin, self).get_urls()

        custom_urls = [
            re_path(r'^$', self.admin_site.admin_view(self.change_view), {'object_id': pk}),
        ]

        return custom_urls + urls

    def save_model(self, request: HttpRequest, obj: GlobalMessage, form: ModelForm, change: bool) -> None:
        obj.updated = request.timestamp
        return super().save_model(request, obj, form, change)


admin.site.register(GlobalMessage, GlobalMessageAdmin)


admin.system_admin_menu_registry.register(
    'globalmessage',
    _("Global message"),
    lambda request: reverse('oioioiadmin:globalmessage_globalmessage_changelist'),
    condition=is_superuser,
    order=20,
)
