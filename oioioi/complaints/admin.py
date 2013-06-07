from oioioi.base import admin
from oioioi.complaints.models import ComplaintsConfig
from oioioi.contests.admin import ContestAdmin


class ComplaintsConfigInline(admin.TabularInline):
    model = ComplaintsConfig


class ComplaintsAdminMixin(object):
    def __init__(self, *args, **kwargs):
        super(ComplaintsAdminMixin, self) \
            .__init__(*args, **kwargs)
        self.inlines = self.inlines + [ComplaintsConfigInline]
ContestAdmin.mix_in(ComplaintsAdminMixin)
