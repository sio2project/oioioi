from django.contrib import messages
from django.utils.translation import ugettext_lazy as _

from oioioi.base import admin
from oioioi.base.forms import AlwaysChangedModelForm
from oioioi.contestexcl.models import ExclusivenessConfig
from oioioi.contests.admin import ContestAdmin


class ExclusivenessConfigInline(admin.TabularInline):
    model = ExclusivenessConfig
    extra = 0
    form = AlwaysChangedModelForm

    def get_readonly_fields(self, request, obj=None):
        if obj and not request.user.is_superuser:
            return self.readonly_fields + ('enabled', 'start_date', 'end_date')
        return ()

    def has_add_permission(self, request):
        return request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        # Protected by parent ModelAdmin and get_readonly_fields
        return True

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser


class ContestAdminWithExclusivenessInlineMixin(object):
    def __init__(self, *args, **kwargs):
        super(ContestAdminWithExclusivenessInlineMixin, self) \
            .__init__(*args, **kwargs)
        self.inlines = self.inlines + [ExclusivenessConfigInline]

    def save_formset(self, request, form, formset, change):
        instances = formset.save()
        for obj in instances:
            if not (isinstance(obj, ExclusivenessConfig) and obj.enabled):
                continue
            qs = ExclusivenessConfig.objects.get_active_between(
                obj.start_date,
                obj.end_date
            ).select_related('contest')
            qs = [ex_conf for ex_conf in qs
                  if ex_conf.contest != request.contest]
            if qs:
                contest_names = ', '.join([ex_conf.contest.name
                                           for ex_conf in qs])
                msg = _("The following contests' exclusion times"
                        " overlap with the current one: %s. Watch out, because"
                        " it may cause conflicts!") % contest_names
                messages.warning(request, msg)
ContestAdmin.mix_in(ContestAdminWithExclusivenessInlineMixin)
