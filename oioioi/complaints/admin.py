from django.utils.translation import gettext_lazy as _

from oioioi.base import admin
from oioioi.complaints.models import ComplaintsConfig
from oioioi.contests.admin import ContestAdmin
from oioioi.contests.utils import is_contest_admin


class ComplaintsConfigInline(admin.TabularInline):
    model = ComplaintsConfig
    category = _("Advanced")

    def has_add_permission(self, request, obj=None):
        return is_contest_admin(request)

    def has_change_permission(self, request, obj=None):
        return is_contest_admin(request)

    def has_delete_permission(self, request, obj=None):
        return is_contest_admin(request)


class ComplaintsAdminMixin(object):
    """Adds :class:`~oioioi.complaints.models.ComplaintConfig` to an admin
    panel.
    """

    def __init__(self, *args, **kwargs):
        super(ComplaintsAdminMixin, self).__init__(*args, **kwargs)
        self.inlines = tuple(self.inlines) + (ComplaintsConfigInline,)


ContestAdmin.mix_in(ComplaintsAdminMixin)
