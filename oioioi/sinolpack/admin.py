from django.contrib import admin
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from oioioi.base.utils import make_html_link
from oioioi.contests.utils import is_contest_admin
from oioioi.sinolpack.models import ExtraConfig, ExtraFile


class SinolpackConfigInline(admin.StackedInline):
    model = ExtraConfig
    can_delete = False
    extra = 0
    max_num = 0
    readonly_fields = ['config']
    fields = readonly_fields
    inline_classes = ('collapse',)
    category = _("Advanced")

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return is_contest_admin(request)

    def has_delete_permission(self, request, obj=None):
        return False

    def has_view_permission(self, request, obj=None):
        return self.has_change_permission(request, obj)


class SinolpackExtraFilesInline(admin.StackedInline):
    model = ExtraFile
    can_delete = False
    extra = 0
    readonly_fields = ['file_link']
    fields = readonly_fields
    inline_classes = ('collapse',)
    category = _("Advanced")

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return is_contest_admin(request)

    def has_delete_permission(self, request, obj=None):
        return False

    def has_view_permission(self, request, obj=None):
        return self.has_change_permission(request, obj)

    def file_link(self, instance):
        if instance.id is not None:
            href = reverse('download_extra_file', kwargs={'file_id': str(instance.id)})
            return make_html_link(href, instance.name)
        return None

    file_link.short_description = _("Extra file")


class SinolpackProblemAdminMixin(object):
    """Adds :class:`~oioioi.sinolpack.models.ExtraConfig` and
    :class:`~oioioi.sinolpack.models.ExtraFile` to an admin panel.
    """

    def __init__(self, *args, **kwargs):
        super(SinolpackProblemAdminMixin, self).__init__(*args, **kwargs)
        self.inlines = tuple(self.inlines) + (SinolpackConfigInline, SinolpackExtraFilesInline,)
