from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils.translation import ugettext_lazy as _
from django.utils.text import get_valid_filename
from oioioi.base.fields import DottedNameField
from oioioi.base.utils import get_object_by_dotted_name
from oioioi.filetracker.fields import FileField

import os.path


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

       Instances of :cls:`Problem` do not represent problems in contests,
       see :cls:`oioioi.contests.models.ProblemInstance` for those.
    """
    name = models.CharField(max_length=255, verbose_name=_("full name"))
    short_name = models.CharField(max_length=30, verbose_name=_("short name"))
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

    class Meta:
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

    class Meta:
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

    class Meta:
        verbose_name = _("attachment")
        verbose_name_plural = _("attachments")

    def __unicode__(self):
        return '%s / %s' % (self.problem.name, self.filename)
