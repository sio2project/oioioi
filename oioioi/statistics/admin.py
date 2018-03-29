from oioioi.base import admin
from oioioi.contests.admin import ContestAdmin
from oioioi.statistics.models import StatisticsConfig


class StatisticsConfigInline(admin.TabularInline):
    model = StatisticsConfig


class StatisticsAdminMixin(object):
    """Adds :class:`~oioioi.statistics.models.StatisticsConfig` to an admin
       panel.
    """

    def __init__(self, *args, **kwargs):
        super(StatisticsAdminMixin, self) \
            .__init__(*args, **kwargs)
        self.inlines = self.inlines + [StatisticsConfigInline]
ContestAdmin.mix_in(StatisticsAdminMixin)
