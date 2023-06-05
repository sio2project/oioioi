from django.contrib.auth.models import User
from django.urls import reverse
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from oioioi.balloons.models import (
    BalloonsDeliveryAccessData,
    BalloonsDisplay,
    ProblemBalloonsConfig,
)
from oioioi.base import admin
from oioioi.base.admin import system_admin_menu_registry
from oioioi.base.utils import make_html_link
from oioioi.contests.admin import ContestAdmin, contest_site
from oioioi.contests.menu import contest_admin_menu_registry
from oioioi.contests.models import Contest, ProblemInstance
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
        return format_html(
            u'<span class="balloons_admin" style="background: {}">' '{}</span>',
            instance.color,
            instance.color,
        )

    color_display.short_description = _("Color")

    def get_queryset(self, request):
        qs = super(ProblemBalloonsConfigAdmin, self).get_queryset(request)
        return qs.filter(problem_instance__contest=request.contest)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'problem_instance':
            qs = ProblemInstance.objects
            if request.contest:
                qs = qs.filter(contest=request.contest)
            kwargs['queryset'] = qs
        return super(ProblemBalloonsConfigAdmin, self).formfield_for_foreignkey(
            db_field, request, **kwargs
        )


contest_site.contest_register(ProblemBalloonsConfig, ProblemBalloonsConfigAdmin)
contest_admin_menu_registry.register(
    'problemballoonsconfig_admin',
    _("Balloon colors"),
    lambda request: reverse('oioioiadmin:balloons_problemballoonsconfig_changelist'),
    is_contest_admin,
    order=60,
)


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

    def get_queryset(self, request):
        qs = super(BalloonsDisplayAdmin, self).get_queryset(request)
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

        return super(BalloonsDisplayAdmin, self).formfield_for_foreignkey(
            db_field, request, **kwargs
        )


admin.site.register(BalloonsDisplay, BalloonsDisplayAdmin)
system_admin_menu_registry.register(
    'balloonsdisplay_admin',
    _("Balloon displays"),
    lambda request: reverse('oioioiadmin:balloons_balloonsdisplay_changelist'),
    order=60,
)


class BalloonsDeliveryAccessDataInline(admin.TabularInline):
    model = BalloonsDeliveryAccessData
    fields = ('access_link', 'valid_until', 'regeneration_link')
    readonly_fields = ('access_link', 'valid_until', 'regeneration_link')
    category = _("Advanced")

    def has_add_permission(self, request, obj=None):
        return is_contest_admin(request)

    def has_change_permission(self, request, obj=None):
        return is_contest_admin(request)

    def has_delete_permission(self, request, obj=None):
        return is_contest_admin(request)

    def access_link(self, instance):
        if instance.access_key:
            url = reverse(
                'balloons_access_set_cookie',
                kwargs={
                    'contest_id': instance.contest.id,
                    'access_key': instance.access_key,
                },
            )
            return make_html_link(url, url)
        else:
            return _("Not yet generated")

    access_link.short_description = _("Access link")

    def regeneration_link(self, instance):
        return make_html_link(
            reverse(
                'balloons_access_regenerate', kwargs={'contest_id': instance.contest.id}
            ),
            _("Regenerate key"),
            'POST',
        )

    regeneration_link.short_description = _("Regeneration link")


class BalloonsDeliveryAccessDataAdminMixin(object):
    """Adds :class:`~oioioi.balloons.BalloonsDeliveryAccessData` fields to an
    admin panel.
    """

    def __init__(self, *args, **kwargs):
        super(BalloonsDeliveryAccessDataAdminMixin, self).__init__(*args, **kwargs)
        self.inlines = tuple(self.inlines) + (BalloonsDeliveryAccessDataInline,)


ContestAdmin.mix_in(BalloonsDeliveryAccessDataAdminMixin)
