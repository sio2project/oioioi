from django.contrib import admin
from django.core.urlresolvers import reverse
from django.utils.translation import ugettext_lazy as _

from oioioi.base.utils import make_html_link
from oioioi.sinolpack.models import ExtraConfig, ExtraFile

class SinolpackConfigInline(admin.StackedInline):
    model = ExtraConfig
    can_delete = False
    extra = 0
    max_num = 0
    readonly_fields = ['config']
    fields = readonly_fields
    inline_classes = ('collapse',)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return True

    def has_delete_permission(self, request, obj=None):
        return False

class SinolpackExtraFilesInline(admin.StackedInline):
    model = ExtraFile
    can_delete = False
    extra = 0
    readonly_fields = ['file_link']
    fields = readonly_fields
    inline_classes = ('collapse',)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return True

    def has_delete_permission(self, request, obj=None):
        return False

    def file_link(self, instance):
        href = reverse('oioioi.sinolpack.views.download_extra_file_view',
            kwargs={'file_id': str(instance.id)})
        return make_html_link(href, instance.name)
    file_link.short_description = _("Extra file")

class SinolpackProblemAdminMixin(object):
    def __init__(self, *args, **kwargs):
        super(SinolpackProblemAdminMixin, self).__init__(*args, **kwargs)
        self.inlines = self.inlines + \
                       [SinolpackConfigInline, SinolpackExtraFilesInline]

