from django.contrib.auth.models import User
from django.urls import reverse
from django.utils.translation import ugettext_lazy as _

from oioioi.base import admin
from oioioi.contests.admin import contest_site
from oioioi.contests.menu import contest_admin_menu_registry
from oioioi.contests.models import Round
from oioioi.base.permissions import is_superuser
from oioioi.supervision.models import Supervision, Group, Membership


class SupervisionAdmin(admin.ModelAdmin):
    list_display = ['group', 'round', 'start_date', 'end_date']
    # list_editable = ['round', 'start_date', 'end_date']
    def get_queryset(self, request):
        qs = super(SupervisionAdmin, self).get_queryset(request)
        return qs.filter(round__contest=request.contest).order_by('start_date')

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'round':
            kwargs['queryset'] = Round.objects.filter(contest=request.contest).order_by(
                'name'
            )
        return super(SupervisionAdmin, self).formfield_for_foreignkey(
            db_field, request, **kwargs
        )

    # def get_list_select_related(self):
    #     return super(SupervisionAdmin, self).get_list_select_related() \
    #            + ['round__contest']


contest_site.contest_register(Supervision, SupervisionAdmin)
contest_admin_menu_registry.register(
    'supervision',
    _("Supervision"),
    lambda request: reverse('oioioiadmin:supervision_supervision_changelist'),
    condition=is_superuser,
    order=40,
)


class MemberAdminInline(admin.TabularInline):
    model = Membership
    extra = 0
    fields = ('is_present', 'user',)
    autocomplete_fields = ('user',)
    User.__str__ = lambda self: "{} {} {}".format(
        self.last_name, self.first_name, self.username
    )

    def get_queryset(self, request):
        qs = super(MemberAdminInline, self).get_queryset(request)
        return qs.order_by('user__username')


class GroupAdmin(admin.ModelAdmin):
    save_on_top = True
    inlines = (MemberAdminInline,)


admin.site.register(Group, GroupAdmin)
admin.system_admin_menu_registry.register(
    'groups',
    _("Groups"),
    lambda request: reverse('oioioiadmin:supervision_group_changelist'),
    order=10,
)
