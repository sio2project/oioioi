from oioioi.base import admin
from oioioi.base.forms import AlwaysChangedModelForm
from oioioi.contests.admin import ProblemInstanceAdmin
from oioioi.testrun.models import TestRunConfig, TestRunConfigForInstance


class TestRunConfigInline(admin.TabularInline):
    model = TestRunConfig
    can_delete = True
    extra = 0
    form = AlwaysChangedModelForm


class TestRunConfigForInstanceInline(admin.TabularInline):
    model = TestRunConfigForInstance
    can_delete = True
    extra = 0
    form = AlwaysChangedModelForm


class TestRunConfigForInstanceInline(admin.TabularInline):
    model = TestRunConfigForInstance
    can_delete = True
    extra = 0
    form = AlwaysChangedModelForm

    def has_add_permission(self, request):
        return True

    def has_change_permission(self, request, obj=None):
        return True

    def has_delete_permission(self, request, obj=None):
        return True


class TestRunProgrammingProblemAdminMixin(object):
    """Adds :class:`~oioioi.testrun.models.TestRunConfig` to an admin panel.
    """

    def __init__(self, *args, **kwargs):
        super(TestRunProgrammingProblemAdminMixin, self) \
            .__init__(*args, **kwargs)
        self.inlines = self.inlines + [TestRunConfigInline]


class TestRunProblemInstanceAdminMixin(object):
    """Adds `TestRunConfigForInstance` to an admin panel.
    """

    def __init__(self, *args, **kwargs):
        super(TestRunProblemInstanceAdminMixin, self) \
            .__init__(*args, **kwargs)
        self.inlines = self.inlines + [TestRunConfigForInstanceInline]

    def get_inline_instances(self, request, obj=None):
        inlines = (super(TestRunProblemInstanceAdminMixin, self)
            .get_inline_instances(request, obj))

        if obj and hasattr(obj.problem, 'test_run_config'):
            return inlines
        else:
            return [inline for inline in inlines
                    if not isinstance(inline, TestRunConfigForInstanceInline)]


# Since ProblemInstanceAdmin isn't an InstanceDependentAdmin (because reasons),
# we don't use the controller to conditionally add the mixin, instead we always
# add it, and check if we should modify the behaviour in the mixin itself.
ProblemInstanceAdmin.mix_in(TestRunProblemInstanceAdminMixin)
