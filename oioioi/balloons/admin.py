from django.core.urlresolvers import reverse
from django.contrib.auth.models import User
from django.utils.translation import ugettext_lazy as _
from oioioi.base import admin
from oioioi.balloons.models import ProblemBalloonsConfig, \
    BalloonsDisplay
from oioioi.base.admin import system_admin_menu_registry
from oioioi.contests.models import ProblemInstance, Contest
from oioioi.contests.menu import contest_admin_menu_registry
from oioioi.contests.utils import is_contest_admin


class ProblemBalloonsConfigAdmin(admin.ModelAdmin):
    list_display = ['problem_instance', 'color_display']
    list_display_links = ['problem_instance']

    def has_add_permission(self, request):
        return is_contest_admin(request)

    def has_change_permission(self, request, obj=None):
        return is_contest_admin(request)

    def has_delete_permission(self, request, obj=None):
        return self.has_change_permission(request, obj)

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return self.readonly_fields + ('problem_instance',)
        return self.readonly_fields

    def color_display(self, instance):
        return '<span class="balloons_admin" style="background: %s">%s' \
               '</span>' % (instance.color, instance.color)
    color_display.allow_tags = True
    color_display.short_description = _("Color")

    def queryset(self, request):
        qs = super(ProblemBalloonsConfigAdmin, self).queryset(request)
        return qs.filter(problem_instance__contest=request.contest)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'problem_instance':
            qs = ProblemInstance.objects
            if request.contest:
                qs = qs.filter(contest=request.contest)
            kwargs['queryset'] = qs
        return super(ProblemBalloonsConfigAdmin, self) \
                .formfield_for_foreignkey(db_field, request, **kwargs)

admin.site.register(ProblemBalloonsConfig, ProblemBalloonsConfigAdmin)
contest_admin_menu_registry.register('problemballoonsconfig_admin',
        _("Balloons colors"), lambda request:
        reverse('oioioiadmin:balloons_problemballoonsconfig_changelist'),
        order=60)


class BalloonsDisplayAdmin(admin.ModelAdmin):
    list_display = ['ip_addr', 'user']

    def has_add_permission(self, request):
        return is_contest_admin(request)

    def has_change_permission(self, request, obj=None):
        return is_contest_admin(request)

    def has_delete_permission(self, request, obj=None):
        return self.has_change_permission(request, obj)

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return self.readonly_fields + ('contest',)
        return self.readonly_fields

    def queryset(self, request):
        qs = super(BalloonsDisplayAdmin, self).queryset(request)
        if request.contest is None:
            return qs
        return qs.filter(contest=request.contest)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if request.contest is not None:
            if db_field.name == 'contest':
                qs = Contest.objects.filter(id=request.contest.id)
                kwargs['initial'] = request.contest
                kwargs['queryset'] = qs
            elif db_field.name == 'user':
                qs = User.objects.filter(participant__contest=request.contest)
                if qs or not request.user.is_superuser:
                    kwargs['queryset'] = qs

        return super(BalloonsDisplayAdmin, self) \
                .formfield_for_foreignkey(db_field, request, **kwargs)

admin.site.register(BalloonsDisplay, BalloonsDisplayAdmin)
system_admin_menu_registry.register('balloonsdisplay_admin',
        _("Balloons displays"), lambda request:
        reverse('oioioiadmin:balloons_balloonsdisplay_changelist'),
        order=60)
