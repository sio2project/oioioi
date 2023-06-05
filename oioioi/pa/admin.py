from django.utils.translation import gettext_lazy as _

from oioioi.base import admin
from oioioi.contests.admin import ProblemInstanceAdmin
from oioioi.contests.utils import is_contest_admin
from oioioi.pa.forms import PARegistrationForm
from oioioi.pa.models import PAProblemInstanceData, PARegistration
from oioioi.participants.admin import ParticipantAdmin


class PARegistrationInline(admin.StackedInline):
    model = PARegistration
    fk_name = 'participant'
    form = PARegistrationForm
    can_delete = False
    inline_classes = ('collapse open',)
    # We don't allow admins to change users' acceptance of contest's terms.
    exclude = ('terms_accepted',)


class PARegistrationParticipantAdmin(ParticipantAdmin):
    list_display = ParticipantAdmin.list_display
    inlines = tuple(ParticipantAdmin.inlines) + (PARegistrationInline,)
    readonly_fields = ['user']

    def has_add_permission(self, request):
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser

    def get_actions(self, request):
        actions = super(PARegistrationParticipantAdmin, self).get_actions(request)
        if 'delete_selected' in actions:
            del actions['delete_selected']
        return actions


class PAProblemInstanceInline(admin.TabularInline):
    model = PAProblemInstanceData
    fields = ['division']

    def has_delete_permission(self, request, obj=None):
        return False

    def get_readonly_fields(self, request, obj=None):
        if is_contest_admin(request):
            return super(PAProblemInstanceInline, self).get_readonly_fields(
                request, obj
            )
        return self.get_fields(request, obj)


class PAProblemInstanceAdminMixin(object):
    """Adds :class:`~oioioi.pa.models.PAProblemInstanceData` to an admin panel."""

    def __init__(self, *args, **kwargs):
        super(PAProblemInstanceAdminMixin, self).__init__(*args, **kwargs)
        self.inlines = tuple(self.inlines) + (PAProblemInstanceInline,)


ProblemInstanceAdmin.mix_in(PAProblemInstanceAdminMixin)
