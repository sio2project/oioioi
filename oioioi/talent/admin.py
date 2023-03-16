from django.conf import settings
from django.contrib import admin
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils.translation import ugettext_lazy as _

from oioioi.base.permissions import make_request_condition
from oioioi.contests.admin import contest_site, contest_admin_menu_registry
from oioioi.talent.models import TalentRegistration


class TalentRegistrationAdmin(admin.ModelAdmin):
    list_display = ['user']
    ordering = ['user__last_name']
    #autocomplete_fields = ['user', 'contest']

    User.__str__ = lambda self: "{} {}".format(self.first_name, self.last_name)
    
    def has_add_permission(self, request):
        return request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser

    def get_queryset(self, request):
        qs = super(TalentRegistrationAdmin, self).get_queryset(request)
        return qs.filter(contest_id=request.contest.id)


@make_request_condition
def is_talent_registration_contest(request):
    return request.contest.id in settings.TALENT_CONTEST_IDS


contest_site.contest_register(TalentRegistration, TalentRegistrationAdmin)
contest_admin_menu_registry.register(
    'talentregistration_change',
    _("Talent participants"),
    lambda request: reverse('oioioiadmin:talent_talentregistration_changelist'),
    condition=is_talent_registration_contest,
    order=200,
)
