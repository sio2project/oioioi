from oioioi.base import admin
from oioioi.base.forms import AlwaysChangedModelForm
from oioioi.contests.admin import ProblemInstanceAdmin
from oioioi.testrun.models import TestRunConfig


class TestRunConfigInline(admin.TabularInline):
    model = TestRunConfig
    can_delete = True
    extra = 0
    form = AlwaysChangedModelForm


class TestRunAdminMixin(object):
    """Adds `TestRunConfigForInstance` to an admin panel."""

    def __init__(self, *args, **kwargs):
        super(TestRunAdminMixin, self).__init__(*args, **kwargs)
        self.inlines = tuple(self.inlines) + (TestRunConfigInline,)

    def get_inlines(self, request, obj=None):
        inlines = super(TestRunAdminMixin, self).get_inlines(request, obj)
        if not obj:
            return inlines
        if not obj.problem.controller.allow_test_runs(request):
            inlines = [inline for inline in inlines if not inline == TestRunConfigInline]
        return inlines


ProblemInstanceAdmin.mix_in(TestRunAdminMixin)
