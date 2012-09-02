from oioioi.base import admin
from oioioi.contestlogo.models import ContestLogo
from oioioi.contests.admin import ContestAdmin

class ContestLogoInline(admin.TabularInline):
    model = ContestLogo

class ContestLogoAdminMixin(object):
    def __init__(self, *args, **kwargs):
        super(ContestLogoAdminMixin, self).__init__(*args, **kwargs)
        self.inlines = self.inlines + [ContestLogoInline]
ContestAdmin.mix_in(ContestLogoAdminMixin)
