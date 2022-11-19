from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.utils.translation import ugettext_lazy as _

from oioioi.base import admin
from oioioi.contests.admin import contest_site
from oioioi.contests.menu import contest_admin_menu_registry
from oioioi.contests.models import Round
from oioioi.supervision.models import Supervision, Group, Membership


class SupervisionAdmin(admin.ModelAdmin):
    # list_display = ['group', 'start_time', 'end_time']
    def get_queryset(self, request):
        qs = super(SupervisionAdmin, self).get_queryset(request)
        return qs.filter(round__contest=request.contest)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'round':
            kwargs['queryset'] = Round.objects.filter(contest=request.contest) \
                .order_by('name')
        return super(SupervisionAdmin, self) \
            .formfield_for_foreignkey(db_field, request, **kwargs)

    # def get_list_select_related(self):
    #     return super(SupervisionAdmin, self).get_list_select_related() \
    #            + ['round__contest']


contest_site.contest_register(Supervision, SupervisionAdmin)
contest_admin_menu_registry.register(
    'supervision',
    _("Supervision"), lambda request: reverse(
        'oioioiadmin:supervision_supervision_changelist'
    ),
    order=40,
)


class MemberAdminInline(admin.StackedInline):
    model = Membership
    extra = 0
    raw_id_fields = ('user',)

    User.__unicode__ = lambda self: u"{} {} ({})".format(
        self.first_name,
        self.last_name,
        self.username)


class GroupAdmin(admin.ModelAdmin):
    inlines = (MemberAdminInline,)


admin.site.register(Group, GroupAdmin)
admin.system_admin_menu_registry.register(
    'groups',
    _("Groups"),
    lambda request: reverse('oioioiadmin:supervision_group_changelist'),
    order=10
)
