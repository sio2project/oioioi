import shutil
import os
import tempfile
import zipfile

from nose.tools import nottest
from django.core.files import File
from django.core.validators import RegexValidator
from django.db import models
from django.db.models.signals import m2m_changed
from django.utils.translation import ugettext_lazy as _

from oioioi.filetracker.fields import FileField
from oioioi.problems.models import Problem, make_problem_filename
from oioioi.programs.models import Test
from oioioi.contests.date_registration import date_registry
from oioioi.contests.models import ProblemInstance


def _testspackage_date_name_generator(obj):
    if TestsPackage.objects.filter(problem=obj.problem).count() == 1:
        return _("Publish tests for %s") % obj.problem.short_name
    return _("Publish tests for %(problem_name)s (%(package_name)s)") % \
            {'problem_name': obj.problem.short_name, 'package_name': obj.name}


def _testspackage_round_chooser(obj):
    qs = ProblemInstance.objects.filter(problem=obj.problem)
    if qs.exists():
        return qs[0].round
    return None


def _testspackage_qs_filter(qs, contest_id):
    return qs.filter(problem__contest=contest_id)


@date_registry.register('publish_date',
                        name_generator=_testspackage_date_name_generator,
                        round_chooser=_testspackage_round_chooser,
                        qs_filter=_testspackage_qs_filter,
                        order=50)
@nottest
class TestsPackage(models.Model):
    problem = models.ForeignKey(Problem)
    name = models.CharField(max_length=30, verbose_name=_("file name"),
            help_text=_("File name can only contain letters, digits,"
                " - and _. It should not contain file extension such as"
                " .zip, .tgz, etc."),
            validators=[RegexValidator(r'^[0-9a-zA-Z\-_]+$',
                _("Name can only contain letters, digits, - and _."))])
    description = models.TextField(null=False, blank=True)
    tests = models.ManyToManyField(Test)
    package = FileField(upload_to=make_problem_filename, null=True,
            blank=True, verbose_name=_("package"))
    publish_date = models.DateTimeField(null=True, blank=True,
            verbose_name=_("publish date"),
            help_text=_("If the date is left blank, the package will never "
                "be visible for participants of the contest."))

    _old_tests = None

    def is_visible(self, current_datetime):
        return self.publish_date is not None and \
                self.publish_date < current_datetime

    class Meta(object):
        verbose_name = _("tests package")
        verbose_name_plural = _("tests packages")


def pack_test_file(test_file, arcname, zip):
    reader = test_file.file
    if hasattr(reader.file, 'name'):
        zip.write(reader.file.name, arcname)
    else:
        with tempfile.NamedTemporaryFile(delete=False) as f:
            shutil.copyfileobj(reader, f)
            f.close()
            zip.write(f.name, arcname)
            os.unlink(f.name)


def _create_tests_package(sender, instance, action, reverse, **kwargs):
    # This function is called upon changing TestsPackage object.
    # The package should be repacked only if set of tests changes
    # but not when, e.g., only the description of package changes.
    if action == 'pre_clear':
        instance._old_tests = list(instance.tests.all())
    elif action == 'post_add':
        if instance._old_tests == list(instance.tests.all()):
            return
        with tempfile.NamedTemporaryFile(delete=False) as f:
            zipf = zipfile.ZipFile(f, 'w', zipfile.ZIP_DEFLATED)
            for test in instance.tests.all():
                for test_file in [test.input_file, test.output_file]:
                    arch_path = os.path.basename(test_file.file.name)
                    pack_test_file(test_file, arch_path, zipf)
            zipf.close()
            instance.package.save('tests.zip', File(f))
            os.unlink(f.name)

m2m_changed.connect(_create_tests_package, sender=TestsPackage.tests.through)
