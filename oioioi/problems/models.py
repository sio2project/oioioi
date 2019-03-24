import logging
import os.path
from contextlib import contextmanager
from traceback import format_exception
from unidecode import unidecode

import six
from django.contrib.auth.models import User
from django.core import validators
from django.core.files.base import ContentFile
from django.core.validators import validate_slug
from django.db import models, transaction
from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver
from django.utils import timezone
from django.utils.module_loading import import_string
from django.utils.text import Truncator, get_valid_filename
from django.utils.translation import pgettext_lazy
from django.utils.translation import ugettext_lazy as _

from oioioi.base.fields import DottedNameField, EnumField, EnumRegistry
from oioioi.base.utils import split_extension, strip_num_or_hash
from oioioi.contests.models import ProblemInstance
from oioioi.filetracker.fields import FileField

logger = logging.getLogger(__name__)


def make_problem_filename(instance, filename):
    if not isinstance(instance, Problem):
        try:
            instance = instance.problem
        except AttributeError:
            assert hasattr(instance, 'problem'), \
                    'problem_file_generator used ' \
                    'on object %r which does not have \'problem\' attribute' \
                    % (instance,)
    return 'problems/%d/%s' % (instance.id,
            get_valid_filename(os.path.basename(filename)))


class Problem(models.Model):
    """Represents a problem in the problems database.

       Instances of :class:`Problem` do not represent problems in contests,
       see :class:`oioioi.contests.models.ProblemInstance` for those.

       Each :class:`Problem` has associated main
       :class:`oioioi.contests.models.ProblemInstance`,
       called main_problem_instance:
       1) It is not assigned to any contest.
       2) It allows sending submissions aside from contests.
       3) It is a base to create another instances.
    """
    name = models.CharField(max_length=255, verbose_name=_("full name"))
    short_name = models.CharField(max_length=30,
            validators=[validate_slug], verbose_name=_("short name"))
    controller_name = DottedNameField(
        'oioioi.problems.controllers.ProblemController',
        verbose_name=_("type"))
    contest = models.ForeignKey('contests.Contest', null=True, blank=True,
                                verbose_name=_("contest"),
                                on_delete=models.SET_NULL)
    author = models.ForeignKey(User, null=True, blank=True,
                               verbose_name=_("author"),
                               on_delete=models.SET_NULL)
    is_public = models.BooleanField(default=False, verbose_name=_("is public"))
    package_backend_name = \
            DottedNameField('oioioi.problems.package.ProblemPackageBackend',
                    null=True, blank=True, verbose_name=_("package type"))
    ascii_name = models.CharField(max_length=255, null=True)  # autofield, no polish characters

    # main_problem_instance:
    # null=True, because there is a cyclic dependency
    # and during creation of any Problem, main_problem_instance
    # must be temporarily set to Null
    # (ProblemInstance has ForeignKey to Problem
    #  and Problem has ForeignKey to ProblemInstance)
    main_problem_instance = models.ForeignKey(
        'contests.ProblemInstance',
        null=True, blank=False, verbose_name=_("main problem instance"),
        related_name='main_problem_instance', on_delete=models.CASCADE
    )

    @property
    def controller(self):
        return import_string(self.controller_name)(self)

    @property
    def package_backend(self):
        return import_string(self.package_backend_name)()

    @classmethod
    def create(cls, *args, **kwargs):
        """Creates a new :class:`Problem` object, with associated
           main_problem_instance.

           After the call, the :class:`Problem` and the
           :class:`ProblemInstance` objects will be saved in the database.
        """
        problem = cls(*args, **kwargs)
        problem.save()
        import oioioi.contests.models
        pi = oioioi.contests.models.ProblemInstance(problem=problem)
        pi.save()
        pi.short_name += "_main"
        pi.save()
        problem.main_problem_instance = pi
        problem.save()
        return problem

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

    def save(self, *args, **kwargs):
        self.ascii_name = unidecode(self.name)
        super(Problem, self).save(*args, **kwargs)


@receiver(post_save, sender=Problem)
def _call_controller_adjust_problem(sender, instance, raw, **kwargs):
    if not raw and instance.controller_name:
        instance.controller.adjust_problem()


@receiver(pre_delete, sender=Problem)
def _check_problem_instance_integrity(sender, instance, **kwargs):
    from oioioi.contests.models import ProblemInstance
    pis = ProblemInstance.objects \
        .filter(problem=instance, contest__isnull=True)
    if pis.count() > 1:
        raise RuntimeError("Multiple main_problem_instance objects for "
                           "a single problem.")


class ProblemStatement(models.Model):
    """Represents a file containing problem statement.

       Problem may have multiple statements, for example in various languages
       or formats. Formats should be detected according to filename extension
       of :attr:`content`.
    """
    problem = models.ForeignKey(Problem, related_name='statements',
                                on_delete=models.CASCADE)
    language = models.CharField(max_length=6, blank=True, null=True,
        verbose_name=_("language code"))
    content = FileField(upload_to=make_problem_filename,
        verbose_name=_("content"))

    @property
    def filename(self):
        return os.path.split(self.content.name)[1]

    @property
    def download_name(self):
        return self.problem.short_name + self.extension

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
    problem = models.ForeignKey(Problem, related_name='attachments',
                                on_delete=models.CASCADE)
    description = models.CharField(max_length=255,
        verbose_name=_("description"))
    content = FileField(upload_to=make_problem_filename,
        verbose_name=_("content"))

    @property
    def filename(self):
        return os.path.split(self.content.name)[1]

    @property
    def download_name(self):
        return strip_num_or_hash(self.filename)

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
                                verbose_name=_("contest"),
                                on_delete=models.SET_NULL)
    problem = models.ForeignKey(Problem, verbose_name=_("problem"), null=True,
                                blank=True, on_delete=models.CASCADE)
    created_by = models.ForeignKey(User, verbose_name=_("created by"),
                                   null=True, blank=True,
                                   on_delete=models.SET_NULL)
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

    @property
    def download_name(self):
        ext = split_extension(self.package_file.name)[1]
        if self.problem:
            return self.problem.short_name + ext
        else:
            filename = os.path.split(self.package_file.name)[1]
            return strip_num_or_hash(filename)

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
                # Truncate error so it doesn't take up whole page in list
                # view. Full info is available anyway in package.traceback.
                package.info = Truncator(value).chars(400)
                package.traceback = ContentFile(
                        ''.join(format_exception(type, value, traceback,
                            TRACEBACK_STACK_LIMIT)),
                        'traceback.txt')
                logger.exception("Error processing package %s",
                        package.package_file.name, extra={'omit_sentry': True})
            else:
                package.status = 'OK'

            # Truncate message to fit in db.
            package.info = Truncator(package.info).chars(1000)

            package.celery_task_id = None
            package.save()
            return True

    def save_operation_status(self):
        """Returns a context manager to be used during the unpacking process.

           The code inside the ``with`` statment is executed in a transaction.

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
            with self.StatusSaver(self), transaction.atomic():
                yield None
        return manager()


class ProblemSite(models.Model):
    """Represents a global problem site.

       Contains configuration necessary to view and submit solutions
       to a :class:`~oioioi.problems.models.Problem`.
    """
    problem = models.OneToOneField(Problem, on_delete=models.CASCADE)
    url_key = models.CharField(max_length=40, unique=True)

    def __unicode__(self):
        return six.text_type(self.problem)

    class Meta(object):
        verbose_name = _("problem site")
        verbose_name_plural = _("problem sites")


class MainProblemInstance(ProblemInstance):
    class Meta(object):
        proxy = True


class ProblemStatistics(models.Model):
    problem = models.OneToOneField(Problem, on_delete=models.CASCADE,
                                   related_name='statistics')
    user_statistics = models.ManyToManyField(User, through='UserStatistics')

    submitted = models.IntegerField(default=0,
                                    verbose_name=_("attempted solutions"))
    solved = models.IntegerField(default=0,
                                 verbose_name=_("correct solutions"))
    avg_best_score = models.IntegerField(default=0,
                                         verbose_name=_("average result"))
    _best_score_sum = models.IntegerField(default=0)


@receiver(post_save, sender=Problem)
def create_statistics_for_new_problem(created, instance, **kwargs):
    if created:
        ProblemStatistics.objects.create(problem=instance)


class UserStatistics(models.Model):
    problem_statistics = models.ForeignKey(ProblemStatistics,
                                           on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    has_submitted = models.BooleanField(default=False,
                                        verbose_name=_("user submitted"))
    has_solved = models.BooleanField(default=False,
                                     verbose_name=_("user solved"))
    best_score = models.IntegerField(default=0,
                                     verbose_name=_("user's best score"))

    class Meta(object):
        unique_together = ('problem_statistics', 'user')


class OriginTag(models.Model):
    name = models.CharField(max_length=20, unique=True,
            verbose_name=_("name"), null=False, blank=False,
            validators=[
                validators.MinLengthValidator(3),
                validators.MaxLengthValidator(20),
                validators.validate_slug,
            ])
    problems = models.ManyToManyField(Problem, through='OriginTagThrough')
    parent_tag = models.ForeignKey('self',
            on_delete=models.CASCADE,
            related_name='child_tags',
            null=True,
            blank=True,
            help_text=("Tag X is the parent of tag Y, if the presence of Y "
                "implies the presence of X. For example: tags with names "
                "'stage 1' and '23' both have the tag with name 'OI' as "
                "parent, which does not have a parent tag of its own. The "
                "tags can be written as a path from their most deep ancestor, "
                "e.g. 'OI / stage 1' or 'OI / 23'. An example of a deeper"
                "hierarchy would be: 'PA / remote / type A' and "
                "'PA / remote / type B' tags, for tagging A/B type tasks from "
                "remote rounds of Potyczki Algorytmiczne. A task can (and "
                "probably should) have multiple origin tags, for example a "
                "task from Potyczki Algorytmiczne could have tags: "
                "'PA / 2010', 'PA / remote / type A', 'PA / remote / round 3', "
                "which also imply tags 'PA / remote' and 'PA'. If you are still "
                "unsure, think of how users will filter the problemset: "
                "'type A' can't be a subtag of 'round 3' or '2010' because "
                "the user will want to search tasks of type A from all rounds "
                "and all years of PA, however type A/B tasks only occur in "
                "remote rounds so we can be more specific and say that "
                "'remote' is the parent of 'type A'."))
    display_depth = models.IntegerField(default=-1,
            help_text=("Sometimes the parent-child relationship does not "
                "convey the full information about the tag hierarchy. Some "
                "tags are more 'broad' than others, and less broad tags "
                "should be grouped under them when displayed (for example in "
                "the task archive). For example you may want to display the "
                "following hierarchy - OI -> year X -> stage Y in year X -> "
                "tasks from stage Y in year X. These tasks would have to be "
                "tagged with 'OI / X' and 'OI / stage Y' so that we can "
                "search for them conveniently, so displaying them in this "
                "particular way requires additional information. The display "
                "depth lets you specify the 'broadness' which the tag has. "
                "For the OI example - 'OI' would have display depth equal to "
                "0, all the 'year X' tags equal to 1, all the 'stage Y' tags "
                "equal to 2. Not all tags have to be used for grouping, and "
                "you may not want to specify the display depth at all (set it "
                "to -1). For instance 'PA / remote / round X' would be depth "
                "2, but 'PA / remote / type A' and 'PA / distributed task' "
                "would be depth -1, since it makes no sense to group "
                "distributed tasks under type A tasks or the other way "
                "around. Display depth of -1 is displayed after all other "
                "depths."))

    class Meta(object):
        verbose_name = _("origin tag")
        verbose_name_plural = _("origin tags")
        unique_together = ('name', 'parent_tag')

    def __unicode__(self):
        return six.text_type(self.name)


class OriginTagThrough(models.Model):
    problem = models.ForeignKey(Problem, on_delete=models.CASCADE)
    tag = models.ForeignKey(OriginTag, on_delete=models.CASCADE)

    # This string will be visible in admin form
    def __unicode__(self):
        return six.text_type(self.tag.name)

    # pylint: disable=w0221
    def save(self, *args, **kwargs):
        instance = super(OriginTagThrough, self).save(*args, **kwargs)
        if self.tag.parent_tag:
            OriginTagThrough.objects.get_or_create(problem=self.problem,
                    tag=self.tag.parent_tag)
        return instance

    class Meta(object):
        unique_together = ('problem', 'tag')


class DifficultyTag(models.Model):
    name = models.CharField(max_length=20, unique=True,
            verbose_name=_("name"), null=False, blank=False,
            validators=[
                validators.MinLengthValidator(3),
                validators.MaxLengthValidator(20),
                validators.validate_slug,
            ])
    problems = models.ManyToManyField(Problem, through='DifficultyTagThrough')

    class Meta(object):
        verbose_name = _("difficulty tag")
        verbose_name_plural = _("difficulty tags")

    def __unicode__(self):
        return six.text_type(self.name)


class DifficultyTagThrough(models.Model):
    problem = models.OneToOneField(Problem, on_delete=models.CASCADE)
    tag = models.ForeignKey(DifficultyTag, on_delete=models.CASCADE)

    # This string will be visible in admin form
    def __unicode__(self):
        return six.text_type(self.tag.name)


class AlgorithmTag(models.Model):
    name = models.CharField(max_length=20, unique=True,
            verbose_name=_("name"), null=False, blank=False,
            validators=[
                validators.MinLengthValidator(3),
                validators.MaxLengthValidator(20),
                validators.validate_slug,
            ])
    problems = models.ManyToManyField(Problem, through='AlgorithmTagThrough')

    class Meta(object):
        verbose_name = _("algorithm tag")
        verbose_name_plural = _("algorithm tags")

    def __unicode__(self):
        return six.text_type(self.name)


class AlgorithmTagThrough(models.Model):
    problem = models.ForeignKey(Problem, on_delete=models.CASCADE)
    tag = models.ForeignKey(AlgorithmTag, on_delete=models.CASCADE)

    # This string will be visible in admin form
    def __unicode__(self):
        return six.text_type(self.tag.name)

    class Meta(object):
        unique_together = ('problem', 'tag')


class Tag(models.Model):
    """Class used for old tags - deprecated."""
    name = models.CharField(max_length=20, unique=True,
            verbose_name=_("name"), null=False, blank=False,
            validators=[
                validators.MinLengthValidator(3),
                validators.MaxLengthValidator(20),
                validators.validate_slug,
            ])
    problems = models.ManyToManyField(Problem, through='TagThrough')

    class Meta(object):
        verbose_name = _("tag")
        verbose_name_plural = _("tags")

    def __unicode__(self):
        return six.text_type(self.name)


class TagThrough(models.Model):
    problem = models.ForeignKey(Problem, on_delete=models.CASCADE)
    tag = models.ForeignKey(Tag, on_delete=models.CASCADE)

    # This string will be visible in admin form
    def __unicode__(self):
        return six.text_type(self.tag.name)

    class Meta(object):
        unique_together = ('problem', 'tag')
