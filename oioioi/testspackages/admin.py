from django.db import models
from django.forms import Textarea
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from oioioi.base import admin
from oioioi.base.admin import NO_CATEGORY
from oioioi.base.utils import make_html_link
from oioioi.contests.utils import is_contest_admin
from oioioi.problems.admin import ProblemAdmin
from oioioi.programs.models import Test
from oioioi.testspackages.forms import TestsPackageInlineFormSet
from oioioi.testspackages.models import TestsPackage


class TestsPackageInline(admin.TabularInline):
    formset = TestsPackageInlineFormSet
    model = TestsPackage
    can_delete = True
    extra = 0
    readonly_fields = ['package_link']
    fields = ['name', 'description', 'tests', 'publish_date', 'package_link']
    problem = None
    formfield_overrides = {
        models.TextField: {'widget': Textarea(attrs={'rows': 10, 'cols': 30})},
    }
    category = NO_CATEGORY

    def has_add_permission(self, request, obj=None):
        return is_contest_admin(request)

    def has_delete_permission(self, request, obj=None):
        return is_contest_admin(request)

    def has_change_permission(self, request, obj=None):
        return is_contest_admin(request)

    def get_formset(self, request, obj=None, **kwargs):
        self.problem = obj
        return super(TestsPackageInline, self).get_formset(request, obj, **kwargs)

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        # It should filter tests from main_problem_instance
        if db_field.name == 'tests' and getattr(self, 'problem', None):
            kwargs['queryset'] = Test.objects.filter(
                problem_instance=self.problem.main_problem_instance
            )
        return super(TestsPackageInline, self).formfield_for_manytomany(
            db_field, request, **kwargs
        )

    def package_link(self, instance):
        if instance.id is not None:
            href = reverse(
                'test',
                kwargs={
                    'package_id': instance.id,
                    'contest_id': instance.problem.contest_id,
                },
            )
            return make_html_link(href, instance.package.file.name)
        return None

    package_link.short_description = _("Package file")


class TestsPackageAdminMixin(object):
    """Adds :class:`~oioioi.testspackages.models.TestsPackage` to an admin
    panel.
    """

    def __init__(self, *args, **kwargs):
        super(TestsPackageAdminMixin, self).__init__(*args, **kwargs)
        self.inlines = tuple(self.inlines) + (TestsPackageInline,)


ProblemAdmin.mix_in(TestsPackageAdminMixin)
