from django.utils.translation import gettext_lazy as _

from oioioi.base import admin
from oioioi.contests.admin import ContestAdmin
from oioioi.mp.controllers import MPContestController
from oioioi.mp.forms import MPRegistrationForm
from oioioi.mp.models import MPRegistration, SubmissionScoreMultiplier
from oioioi.participants.admin import ParticipantAdmin


class MPRegistrationInline(admin.StackedInline):
    model = MPRegistration
    fk_name = 'participant'
    form = MPRegistrationForm
    can_delete = False
    inline_classes = ('collapse open',)
    # We don't allow admins to change users' acceptance of contest's terms.
    exclude = ('terms_accepted',)


class MPRegistrationParticipantAdmin(ParticipantAdmin):
    list_display = ParticipantAdmin.list_display
    inlines = tuple(ParticipantAdmin.inlines) + (MPRegistrationInline,)
    readonly_fields = ['user']

    def has_add_permission(self, request):
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser

    def get_actions(self, request):
        actions = super(MPRegistrationParticipantAdmin, self).get_actions(request)
        if 'delete_selected' in actions:
            del actions['delete_selected']
        return actions


class SubmissionScoreMultiplierInline(admin.TabularInline):
    model = SubmissionScoreMultiplier
    extra = 0
    category = _("Advanced")


class SubmissionScoreMultiplierAdminMixin(object):
    """Adds :class:`~oioioi.mp.models.SubmissionScoreMultiplier` to an admin panel
    when contest controller is MPContestController.
    """

    def get_inlines(self, request, obj):
        inlines = super().get_inlines(request, obj)
        if hasattr(obj, 'controller') and isinstance(
            obj.controller, MPContestController
        ):
            return inlines + (SubmissionScoreMultiplierInline,)
        return inlines


ContestAdmin.mix_in(SubmissionScoreMultiplierAdminMixin)
