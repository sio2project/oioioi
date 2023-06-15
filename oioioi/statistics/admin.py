from django.utils.translation import gettext_lazy as _

from oioioi.base import admin
from oioioi.contests.admin import ContestAdmin
from oioioi.contests.utils import is_contest_admin
from oioioi.statistics.models import StatisticsConfig


class StatisticsConfigInline(admin.TabularInline):
    model = StatisticsConfig
    category = _("Advanced")

    def has_add_permission(self, request, obj=None):
        return is_contest_admin(request)

    def has_change_permission(self, request, obj=None):
        return is_contest_admin(request)

    def has_delete_permission(self, request, obj=None):
        return is_contest_admin(request)

    def has_view_permission(self, request, obj=None):
        return self.has_change_permission(request, obj)


class StatisticsAdminMixin(object):
    """Adds :class:`~oioioi.statistics.models.StatisticsConfig` to an admin
    panel.
    """

    def __init__(self, *args, **kwargs):
        super(StatisticsAdminMixin, self).__init__(*args, **kwargs)
        self.inlines = tuple(self.inlines) + (StatisticsConfigInline,)


ContestAdmin.mix_in(StatisticsAdminMixin)
