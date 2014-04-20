import logging
import os.path
from contextlib import contextmanager
from traceback import format_exception

from django.core.validators import validate_slug
from django.core.files.base import ContentFile
from django.db import models, transaction
from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _, pgettext_lazy
from django.utils.text import get_valid_filename
from django.contrib.auth.models import User

from oioioi.base.fields import DottedNameField, EnumRegistry, EnumField
from oioioi.base.utils import get_object_by_dotted_name
from oioioi.filetracker.fields import FileField


logger = logging.getLogger(__name__)


def make_problem_filename(instance, filename):
    if not isinstance(instance, Problem):
        assert hasattr(instance, 'problem'), 'problem_file_generator used ' \
                'on object %r which does not have \'problem\' attribute' \
                % (instance,)
        instance = getattr(instance, 'problem')
    return 'problems/%d/%s' % (instance.id,
            get_valid_filename(os.path.basename(filename)))


class Problem(models.Model):
    """Represents a problem in the problems database.

       Instances of :class:`Problem` do not represent problems in contests,
       see :class:`oioioi.contests.models.ProblemInstance` for those.
    """
    name = models.CharField(max_length=255, verbose_name=_("full name"))
    short_name = models.CharField(max_length=30,
            validators=[validate_slug], verbose_name=_("short name"))
    controller_name = DottedNameField(
        'oioioi.problems.controllers.ProblemController',
        verbose_name=_("type"))
    contest = models.ForeignKey('contests.Contest', null=True, blank=True,
        verbose_name=_("contest"))
    package_backend_name = \
            DottedNameField('oioioi.problems.package.ProblemPackageBackend',
                    null=True, blank=True, verbose_name=_("package type"))

    @property
    def controller(self):
        return get_object_by_dotted_name(self.controller_name)(self)

    @property
    def package_backend(self):
        return get_object_by_dotted_name(self.package_backend_name)()

    class Meta(object):
        verbose_name = _("problem")
        verbose_name_plural = _("problems")
        permissions = (
            ('problems_db_admin', _("Can administer the problems database")),
            ('problem_admin', _("Can administer the problem")),
        )

    def __unicode__(self):
        return '%(name)s (%(short_name)s)' % \
                dict(short_name=self.short_name, name=self.name)


@receiver(post_save, sender=Problem)
def _call_controller_adjust_problem(sender, instance, raw, **kwargs):
    if not raw and instance.controller_name:
        instance.controller.adjust_problem()


@receiver(pre_delete, sender=Problem)
def _check_problem_instance_integrity(sender, instance, **kwargs):
    from oioioi.contests.models import ProblemInstance
    pis = ProblemInstance.objects.filter(problem=instance)
    if pis.count() > 1:
        raise RuntimeError("Multiple ProblemInstance objects for a single "
                    "problem. Please reopen "
                    "https://jira.sio2project.mimuw.edu.pl/browse/SIO-1517")


class ProblemStatement(models.Model):
    """Represents a file containing problem statement.

       Problem may have multiple statements, for example in various languages
       or formats. Formats should be detected according to filename extension
       of :attr:`content`.
    """
    problem = models.ForeignKey(Problem, related_name='statements')
    language = models.CharField(max_length=6, blank=True, null=True,
        verbose_name=_("language code"))
    content = FileField(upload_to=make_problem_filename,
        verbose_name=_("content"))

    @property
    def filename(self):
        return os.path.split(self.content.name)[1]

    @property
    def extension(self):
        return os.path.splitext(self.content.name)[1].lower()

    class Meta(object):
        verbose_name = _("problem statement")
        verbose_name_plural = _("problem statements")

    def __unicode__(self):
        return '%s / %s' % (self.problem.name, self.filename)


class ProblemAttachment(models.Model):
    """Represents an additional file visible to the contestant, linked to
       a problem.

       This may be used for things like input data for open data tasks, or for
       giving users additional libraries etc.
    """
    problem = models.ForeignKey(Problem, related_name='attachments')
    description = models.CharField(max_length=255,
        verbose_name=_("description"))
    content = FileField(upload_to=make_problem_filename,
        verbose_name=_("content"))

    @property
    def filename(self):
        return os.path.split(self.content.name)[1]

    class Meta(object):
        verbose_name = _("attachment")
        verbose_name_plural = _("attachments")

    def __unicode__(self):
        return '%s / %s' % (self.problem.name, self.filename)


def _make_package_filename(instance, filename):
    if instance.contest:
        contest_name = instance.contest.id
    else:
        contest_name = 'no_contest'
    return 'package/%s/%s' % (contest_name,
            get_valid_filename(os.path.basename(filename)))

package_statuses = EnumRegistry()
package_statuses.register('?', pgettext_lazy("Pending",
        "Pending problem package"))
package_statuses.register('OK', _("Uploaded"))
package_statuses.register('ERR', _("Error"))

TRACEBACK_STACK_LIMIT = 100


class ProblemPackage(models.Model):
    """Represents a file with data necessary for creating a
       :class:`~oioioi.problems.models.Problem` instance.
    """
    package_file = FileField(upload_to=_make_package_filename,
        verbose_name=_("package"))
    contest = models.ForeignKey('contests.Contest', null=True, blank=True,
        verbose_name=_("contest"))
    problem = models.ForeignKey(Problem, verbose_name=_("problem"), null=True,
            blank=True)
    created_by = models.ForeignKey(User, verbose_name=_("created by"),
            null=True, blank=True)
    problem_name = models.CharField(max_length=30, validators=[validate_slug],
            verbose_name=_("problem name"), null=True, blank=True)
    celery_task_id = models.CharField(max_length=50, unique=True, null=True,
                                      blank=True)
    info = models.CharField(max_length=1000, null=True, blank=True,
            verbose_name=_("Package information"))
    traceback = FileField(upload_to=_make_package_filename,
            verbose_name=_("traceback"), null=True, blank=True)
    status = EnumField(package_statuses, default='?', verbose_name=_("status"))
    creation_date = models.DateTimeField(default=timezone.now)

    class Meta(object):
        verbose_name = _("problem package")
        verbose_name_plural = _("problem packages")
        ordering = ['-creation_date']

    class StatusSaver(object):
        def __init__(self, package):
            self.package_id = package.id

        def __enter__(self):
            pass

        def __exit__(self, type, value, traceback):
            package = ProblemPackage.objects.get(id=self.package_id)
            if type:
                package.status = 'ERR'
                package.info = value
                package.traceback = ContentFile(
                        ''.join(format_exception(type, value, traceback,
                            TRACEBACK_STACK_LIMIT)),
                        'traceback.txt')
                logger.exception("Error processing package %s",
                        package.package_file.name)
            else:
                package.status = 'OK'

            package.celery_task_id = None
            package.save()
            return True

    def save_operation_status(self):
        """Returns a context manager to be used during the unpacking process.

           The code inside the ``with`` statment is executed in the
           ``commit_on_success`` transaction mode.

           If the code inside the ``with`` statement executes successfully,
           the package ``status`` field is set to ``OK``.

           If an exception is thrown, it gets logged together with the
           traceback. Additionally, its value is saved in the package
           ``info`` field.

           Lastly, if the package gets deleted from the database before
           the ``with`` statement ends, a
           :class:`oioioi.problems.models.ProblemPackage.DoesNotExist`
           exception is thrown.
        """
        @contextmanager
        def manager():
            with self.StatusSaver(self), transaction.commit_on_success():
                yield None
        return manager()
