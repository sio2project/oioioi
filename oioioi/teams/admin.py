from django.core.urlresolvers import reverse
from django.utils.translation import ugettext_lazy as _
from oioioi.base import admin
from oioioi.contests.menu import contest_admin_menu_registry
from oioioi.contests.utils import is_contest_admin
from oioioi.contests.admin import ContestAdmin
from oioioi.teams.forms import TeamForm
from oioioi.teams.models import Team, TeamMembership, TeamsConfig
from oioioi.teams.utils import teams_enabled


class MembersInline(admin.TabularInline):
    model = TeamMembership
    fields = ['user', ]


class TeamsAdmin(admin.ModelAdmin):
    list_select_related = True
    list_display = ['name', 'join_key']
    fields = ['name', 'login']
    search_fields = ['name']
    inlines = [MembersInline, ]
    form = TeamForm

    def has_add_permission(self, request):
        return is_contest_admin(request)

    def has_change_permission(self, request, obj=None):
        return is_contest_admin(request)

    def has_delete_permission(self, request, obj=None):
        return self.has_change_permission(request, obj)

    def get_queryset(self, request):
        qs = super(TeamsAdmin, self).get_queryset(request)
        qs = qs.filter(contest=request.contest)
        return qs

    def save_model(self, request, obj, form, change):
        obj.contest = request.contest
        obj.save()


admin.site.register(Team, TeamsAdmin)
contest_admin_menu_registry.register('teams', _("Teams"),
    lambda request: reverse('oioioiadmin:teams_team_changelist'),
    condition=teams_enabled, order=30)


class TeamsConfigInline(admin.TabularInline):
    model = TeamsConfig


class TeamsAdminMixin(object):
    def __init__(self, *args, **kwargs):
        super(TeamsAdminMixin, self).__init__(*args, **kwargs)
        self.inlines = self.inlines + [TeamsConfigInline]
ContestAdmin.mix_in(TeamsAdminMixin)
