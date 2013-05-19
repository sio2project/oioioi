from oioioi.base import admin
from oioioi.base.forms import AlwaysChangedModelForm
from oioioi.testrun.models import TestRunConfig

class TestRunConfigInline(admin.TabularInline):
    model = TestRunConfig
    can_delete = True
    extra = 0
    form = AlwaysChangedModelForm

class TestRunProgrammingProblemAdminMixin(object):
    def __init__(self, *args, **kwargs):
        super(TestRunProgrammingProblemAdminMixin, self) \
            .__init__(*args, **kwargs)
        self.inlines = self.inlines + [TestRunConfigInline]
