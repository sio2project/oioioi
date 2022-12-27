from django.contrib import admin
from django.contrib.admin import SimpleListFilter
from django.urls import reverse
from django.utils.translation import ugettext_lazy as _

from oioioi.base.permissions import make_request_condition
from oioioi.contests.admin import contest_site, contest_admin_menu_registry
from oioioi.contests.models import Round
from oioioi.contests.utils import is_contest_admin
from oioioi.phase.models import Phase


class PhaseListFilter(SimpleListFilter):
    title = _("round")
    parameter_name = 'round'

    def lookups(self, request, model_admin):
        qs = model_admin.get_queryset(request)
        return Round.objects.filter(id__in=qs.values_list('round')).values_list(
            'id', 'name'
        )

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(round=self.value())
        else:
            return queryset


class PhaseAdmin(admin.ModelAdmin):
    list_display = ['round', 'start_date', 'multiplier']
    list_display_links = ['start_date']
    list_filter = [PhaseListFilter]
    search_fields = []

    def has_add_permission(self, request):
        return is_contest_admin(request)

    def has_change_permission(self, request, obj=None):
        return is_contest_admin(request)

    def has_delete_permission(self, request, obj=None):
        return self.has_change_permission(request, obj)

    def get_queryset(self, request):
        qs = super(PhaseAdmin, self).get_queryset(request)
        return qs.filter(round__contest=request.contest)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'round':
            kwargs['queryset'] = Round.objects.filter(contest=request.contest)
        return super(PhaseAdmin, self).formfield_for_foreignkey(
            db_field, request, **kwargs
        )

    # def get_list_select_related(self):
    #     return super(PhaseAdmin, self).get_list_select_related() \
    #            + ['round__contest']


@make_request_condition
def is_phase_contest(request):
    return hasattr(request.contest, 'controller') and request.contest.controller.is_phase_contest


contest_site.contest_register(Phase, PhaseAdmin)
contest_admin_menu_registry.register(
    'phase_change',
    _("Phases"),
    lambda request: reverse('oioioiadmin:phase_phase_changelist'),
    condition=is_phase_contest,
    order=44,
)
