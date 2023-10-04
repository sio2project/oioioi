from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from oioioi.base import admin
from oioioi.contests.admin import ContestAdmin, contest_site
from oioioi.contests.menu import contest_admin_menu_registry
from oioioi.contests.utils import is_contest_admin
from oioioi.teams.forms import TeamForm
from oioioi.teams.models import Team, TeamMembership, TeamsConfig
from oioioi.teams.utils import teams_enabled


class MembersInline(admin.TabularInline):
    model = TeamMembership
    fields = [
        'user',
    ]


class TeamsAdmin(admin.ModelAdmin):
    list_select_related = True
    list_display = ['name', 'join_key']
    fields = ['name', 'login']
    search_fields = ['name']
    inlines = (
        MembersInline,
    )
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

    def save_form(self, request, *args, **kwargs):
        obj = super(TeamsAdmin, self).save_form(request, *args, **kwargs)
        obj.contest = request.contest
        return obj


contest_site.contest_register(Team, TeamsAdmin)
contest_admin_menu_registry.register(
    'teams',
    _("Teams"),
    lambda request: reverse('oioioiadmin:teams_team_changelist'),
    condition=teams_enabled & is_contest_admin,
    order=30,
)


class TeamsConfigInline(admin.TabularInline):
    model = TeamsConfig
    category = _("Advanced")

    def has_add_permission(self, request, obj=None):
        return is_contest_admin(request)

    def has_change_permission(self, request, obj=None):
        return is_contest_admin(request)

    def has_delete_permission(self, request, obj=None):
        return self.has_change_permission(request, obj)


class TeamsAdminMixin(object):
    """Adds :class:`~oioioi.teams.models.TeamsConfig` to an admin panel."""

    def __init__(self, *args, **kwargs):
        super(TeamsAdminMixin, self).__init__(*args, **kwargs)
        self.inlines = tuple(self.inlines) + (TeamsConfigInline,)


ContestAdmin.mix_in(TeamsAdminMixin)
