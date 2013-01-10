from oioioi.base import admin
from oioioi.testrun.models import TestRunConfig
from django.forms.models import ModelForm

# http://stackoverflow.com/questions/3657709/how-to-force-save-an-empty-unchanged-django-admin-inline
class AlwaysChangedModelForm(ModelForm):
    def has_changed(self):
        """By always returning True even unchanged inlines will get saved."""
        return True

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
