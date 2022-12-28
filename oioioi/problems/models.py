import logging
import os.path
from contextlib import contextmanager
from traceback import format_exception

from django.conf import settings
from django.contrib.auth.models import User
from django.core import validators
from django.core.files.base import ContentFile
from django.core.validators import validate_slug
from django.db import models, transaction
from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver
from django.utils import timezone
from django.utils.encoding import force_str
from django.utils.functional import cached_property
from django.utils.module_loading import import_string
from django.utils.text import get_valid_filename
from django.utils.translation import get_language, pgettext_lazy
from django.utils.translation import gettext_lazy as _
from oioioi.base.fields import DottedNameField, EnumField, EnumRegistry
from oioioi.base.utils import split_extension, strip_num_or_hash
from oioioi.contests.models import ProblemInstance
from oioioi.filetracker.fields import FileField
from oioioi.problems.validators import validate_origintag
from unidecode import unidecode

logger = logging.getLogger(__name__)


def make_problem_filename(instance, filename):
    if not isinstance(instance, Problem):
        try:
            instance = instance.problem
        except AttributeError:
            assert hasattr(instance, 'problem'), (
                'problem_file_generator used '
                'on object %r which does not have \'problem\' attribute' % (instance,)
            )
    return 'problems/%d/%s' % (
        instance.id,
        get_valid_filename(os.path.basename(filename)),
    )



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

    legacy_name = models.CharField(max_length=255, verbose_name=_("legacy name"))
    short_name = models.CharField(
        max_length=30, validators=[validate_slug], verbose_name=_("short name")
    )
    controller_name = DottedNameField(
        'oioioi.problems.controllers.ProblemController', verbose_name=_("type")
    )
    contest = models.ForeignKey(
        'contests.Contest',
        null=True,
        blank=True,
        verbose_name=_("contest"),
        on_delete=models.SET_NULL,
    )
    author = models.ForeignKey(
        User, null=True, blank=True, verbose_name=_("author"), on_delete=models.SET_NULL
    )
    # visibility defines read access to all of problem data (this includes
    # the package, all tests and attachments)
    VISIBILITY_PUBLIC = 'PU'
    VISIBILITY_FRIENDS = 'FR'
    VISIBILITY_PRIVATE = 'PR'
    VISIBILITY_LEVELS_CHOICES = [
        (VISIBILITY_PUBLIC, 'Public'),
        (VISIBILITY_FRIENDS, 'Friends'),
        (VISIBILITY_PRIVATE, 'Private'),
    ]
    visibility = models.CharField(
        max_length=2,
        verbose_name=_("visibility"),
        choices=VISIBILITY_LEVELS_CHOICES,
        default=VISIBILITY_FRIENDS,
    )
    package_backend_name = DottedNameField(
        'oioioi.problems.package.ProblemPackageBackend',
        null=True,
        blank=True,
        verbose_name=_("package type"),
    )
    ascii_name = models.CharField(
        max_length=255, null=True
    )  # autofield, no polish characters

    # main_problem_instance:
    # null=True, because there is a cyclic dependency
    # and during creation of any Problem, main_problem_instance
    # must be temporarily set to Null
    # (ProblemInstance has ForeignKey to Problem
    #  and Problem has ForeignKey to ProblemInstance)
    main_problem_instance = models.ForeignKey(
        'contests.ProblemInstance',
        null=True,
        blank=False,
        verbose_name=_("main problem instance"),
        related_name='main_problem_instance',
        on_delete=models.CASCADE,
    )

    @cached_property
    def name(self):
        problem_name = ProblemName.objects.filter(
            problem=self, language=get_language()
        ).first()
        return problem_name.name if problem_name else self.legacy_name

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

    def __str__(self):
        return u'%(name)s (%(short_name)s)' % {
            u'short_name': self.short_name,
            u'name': self.name,
        }

    def save(self, *args, **kwargs):
        self.ascii_name = unidecode(str(self.name))
        super(Problem, self).save(*args, **kwargs)


@receiver(post_save, sender=Problem)
def _call_controller_adjust_problem(sender, instance, raw, **kwargs):
    if not raw and instance.controller_name:
        instance.controller.adjust_problem()


@receiver(pre_delete, sender=Problem)
def _check_problem_instance_integrity(sender, instance, **kwargs):
    from oioioi.contests.models import ProblemInstance

    pis = ProblemInstance.objects.filter(problem=instance, contest__isnull=True)
    if pis.count() > 1:
        raise RuntimeError(
            "Multiple main_problem_instance objects for a single problem."
        )


class ProblemName(models.Model):
    """Represents a problem's name translation in a given language.

    Problem should have its name translated to all available languages.
    """

    problem = models.ForeignKey(Problem, related_name='names', on_delete=models.CASCADE)
    name = models.CharField(
        max_length=255,
        verbose_name=_("name translation"),
        help_text=_("Human-readable name."),
    )
    language = models.CharField(
        max_length=2, choices=settings.LANGUAGES, verbose_name=_("language code")
    )

    class Meta(object):
        unique_together = ('problem', 'language')
        verbose_name = _("problem name")
        verbose_name_plural = _("problem names")

    def __str__(self):
        return str("{} - {}".format(self.problem, self.language))


class ProblemStatement(models.Model):
    """Represents a file containing problem statement.

    Problem may have multiple statements, for example in various languages
    or formats. Formats should be detected according to filename extension
    of :attr:`content`.
    """

    problem = models.ForeignKey(
        Problem, related_name='statements', on_delete=models.CASCADE
    )
    language = models.CharField(
        max_length=6, blank=True, null=True, verbose_name=_("language code")
    )
    content = FileField(upload_to=make_problem_filename, verbose_name=_("content"))

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

    def __str__(self):
        return u'%s / %s' % (self.problem.name, self.filename)



class ProblemAttachment(models.Model):
    """Represents an additional file visible to the contestant, linked to
    a problem.

    This may be used for things like input data for open data tasks, or for
    giving users additional libraries etc.
    """

    problem = models.ForeignKey(
        Problem, related_name='attachments', on_delete=models.CASCADE
    )
    description = models.CharField(max_length=255, verbose_name=_("description"))
    content = FileField(upload_to=make_problem_filename, verbose_name=_("content"))

    @property
    def filename(self):
        return os.path.split(self.content.name)[1]

    @property
    def download_name(self):
        return strip_num_or_hash(self.filename)

    class Meta(object):
        verbose_name = _("attachment")
        verbose_name_plural = _("attachments")

    def __str__(self):
        return u'%s / %s' % (self.problem.name, self.filename)


def _make_package_filename(instance, filename):
    if instance.contest_id:
        contest_name = instance.contest_id
    else:
        contest_name = 'no_contest'
    return 'package/%s/%s' % (
        contest_name,
        get_valid_filename(os.path.basename(filename)),
    )


package_statuses = EnumRegistry()
package_statuses.register('?', pgettext_lazy("Pending", "Pending problem package"))
package_statuses.register('OK', _("Uploaded"))
package_statuses.register('ERR', _("Error"))

TRACEBACK_STACK_LIMIT = 100


def truncate_unicode(string, length, encoding='utf-8'):
    """ Truncates string to be `length` bytes long. """
    encoded = string.encode(encoding)[:length]
    return encoded.decode(encoding, 'ignore')


class ProblemPackage(models.Model):
    """Represents a file with data necessary for creating a
    :class:`~oioioi.problems.models.Problem` instance.
    """

    package_file = FileField(
        upload_to=_make_package_filename, verbose_name=_("package")
    )
    contest = models.ForeignKey(
        'contests.Contest',
        null=True,
        blank=True,
        verbose_name=_("contest"),
        on_delete=models.SET_NULL,
    )
    problem = models.ForeignKey(
        Problem,
        verbose_name=_("problem"),
        null=True,
        blank=True,
        on_delete=models.CASCADE,
    )
    created_by = models.ForeignKey(
        User,
        verbose_name=_("created by"),
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    problem_name = models.CharField(
        max_length=30,
        validators=[validate_slug],
        verbose_name=_("problem name"),
        null=True,
        blank=True,
    )
    celery_task_id = models.CharField(max_length=50, unique=True, null=True, blank=True)
    info = models.CharField(
        max_length=1000, null=True, blank=True, verbose_name=_("Package information")
    )
    traceback = FileField(
        upload_to=_make_package_filename,
        verbose_name=_("traceback"),
        null=True,
        blank=True,
    )
    status = EnumField(package_statuses, default='?', verbose_name=_("status"))
    creation_date = models.DateTimeField(
        default=timezone.now, verbose_name=_("creation date")
    )

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

                try:
                    # This will work if a PackageProcessingError was thrown
                    info = _(
                        u"Failed operation: %(name)s\n"
                        u"Operation description: %(desc)s\n \n"
                        u"Error description: %(error)r\n \n"
                        % dict(
                            name=value.raiser,
                            desc=value.raiser_desc,
                            error=value.original_exception_info[1],
                        )
                    )

                    type, value, _old_traceback = value.original_exception_info
                except AttributeError:
                    info = _(
                        u"Failed operation unknown.\n"
                        u"Error description: %(error)s\n \n" % dict(error=value)
                    )

                # Truncate error so it doesn't take up whole page in list
                # view (or much space in the database).
                # Full info is available in package.traceback anyway.
                package.info = truncate_unicode(
                    info, ProblemPackage._meta.get_field('info').max_length
                )

                package.traceback = ContentFile(
                    force_str(info)
                    + ''.join(
                        format_exception(type, value, traceback, TRACEBACK_STACK_LIMIT)
                    ),
                    'traceback.txt',
                )
                logger.exception(
                    "Error processing package %s",
                    package.package_file.name,
                    extra={'omit_sentry': True},
                )
            else:
                package.status = 'OK'

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

    def __str__(self):
        return str(self.problem)

    class Meta(object):
        verbose_name = _("problem site")
        verbose_name_plural = _("problem sites")


class MainProblemInstance(ProblemInstance):
    class Meta(object):
        proxy = True


class ProblemStatistics(models.Model):
    problem = models.OneToOneField(
        Problem, on_delete=models.CASCADE, related_name='statistics'
    )
    user_statistics = models.ManyToManyField(User, through='UserStatistics')

    submitted = models.IntegerField(default=0, verbose_name=_("attempted solutions"))
    solved = models.IntegerField(default=0, verbose_name=_("correct solutions"))
    avg_best_score = models.IntegerField(default=0, verbose_name=_("average result"))
    _best_score_sum = models.IntegerField(default=0)


class UserStatistics(models.Model):
    problem_statistics = models.ForeignKey(ProblemStatistics, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    has_submitted = models.BooleanField(default=False, verbose_name=_("user submitted"))
    has_solved = models.BooleanField(default=False, verbose_name=_("user solved"))
    best_score = models.IntegerField(default=0, verbose_name=_("user's best score"))

    class Meta(object):
        unique_together = ('problem_statistics', 'user')


def _localized(*localized_fields):
    """Some models may have fields with language-specific data, which cannot be
    translated through the normal internalization tools, as it is not
    defined in the source code (e.g. names of dynamically defined items).

    Decorate a class with this decorator when there exists a class that:
     - has a ForeignKey to the decorated class with a related_name
       of `localizations`.
     - has a `language` field, and all of `localized_fields`.
    The `localized_fields` can then be accessed directly through the
    decorated class, and will be matched to the current language.

    Be sure to use prefetch_related('localizations') if you will be
    querying multiple localized model instances!

    Also see: LocalizationForm
    """

    def decorator(cls):
        def localize(self, key):
            language = get_language()
            # In case prefetch_related('localizations') was done don't want to
            # use filter to avoid database queries. If it wasn't - querying one
            # language vs all languages is not too much of a difference anyway.
            for localization in self.localizations.all():
                if localization.language == language:
                    return getattr(localization, key)
            return None

        def __getattr__(self, key):
            if key in self.localized_fields:
                return self.localize(key)
            else:
                raise AttributeError(
                    "'{}' object has no attribute '{}'".format(cls.__name__, key)
                )

        cls.localized_fields = localized_fields
        cls.localize = localize
        cls.__getattr__ = __getattr__
        return cls

    return decorator


@_localized('short_name', 'full_name', 'description')

class OriginTag(models.Model):
    """OriginTags are used along with OriginInfoCategories and OriginInfoValue
    to give information about the problem's origin. OriginTags themselves
    represent general information about a problem's origin, whereas
    OriginInfoValues grouped under OriginInfoCategories represent more
    specific information. A Problem should probably not have more than one
    OriginTag, and should probably have one OriginInfoValue for each
    category.

    See also: OriginInfoCategory, OriginInfoValue
    """

    name = models.CharField(
        max_length=20,
        validators=(validate_origintag,),
        verbose_name=_("name"),
        help_text=_(
            "Short, searchable name consisting only of lowercase letters, numbers, "
            "and hyphens.<br>"
            "This should refer to general origin, i.e. a particular contest, "
            "competition, programming camp, etc.<br>"
            "This will be displayed verbatim in the Problemset."
        ),
    )
    problems = models.ManyToManyField(
        Problem,
        blank=True,
        verbose_name=_("problems"),
        help_text=_("Selected problems will be tagged with this tag.<br>"),
    )

    class Meta(object):
        verbose_name = _("origin tag")
        verbose_name_plural = _("origin tags")

    def __str__(self):
        return str(self.name)



class OriginTagLocalization(models.Model):
    origin_tag = models.ForeignKey(
        OriginTag, related_name='localizations', on_delete=models.CASCADE
    )
    language = models.CharField(
        max_length=2, choices=settings.LANGUAGES, verbose_name=_("language")
    )
    full_name = models.CharField(
        max_length=255,
        verbose_name=_("full name"),
        help_text=_(
            "Full, official name of the contest, competition, programming camp, etc. "
            "which this tag represents."
        ),
    )
    short_name = models.CharField(
        max_length=32,
        blank=True,
        verbose_name=_("abbreviation"),
        help_text=_("(optional) Official abbreviation of the full name."),
    )
    description = models.TextField(
        blank=True,
        verbose_name=_("description"),
        help_text=_(
            "(optional) Longer description which Will be displayed in the "
            "Task Archive next to the name."
        ),
    )

    class Meta(object):
        unique_together = ('origin_tag', 'language')
        verbose_name = _("origin tag localization")
        verbose_name_plural = _("origin tag localizations")

    def __str__(self):
        return str("{} - {}".format(self.origin_tag, self.language))


@_localized('full_name')

class OriginInfoCategory(models.Model):
    """This class represents a category of information, which further specifies
    what its parent_tag is already telling about the origin. It doesn't do
    much by itself and is instead used to group OriginInfoValues by category

    See also: OriginTag, OriginInfoValue
    """

    parent_tag = models.ForeignKey(
        OriginTag,
        related_name='info_categories',
        on_delete=models.CASCADE,
        verbose_name=_("parent tag"),
        help_text=_(
            "This category will be a possible category of information for problems "
            "tagged with the selected tag."
        ),
    )
    name = models.CharField(
        max_length=20,
        validators=(validate_origintag,),
        verbose_name=_("name"),
        help_text=_(
            "Type of information within this category. Short, searchable name "
            "consisting of only lowercase letters, numbers, and hyphens.<br>"
            "Examples: 'year', 'edition', 'stage', 'day'."
        ),
    )
    order = models.IntegerField(
        blank=True,
        null=True,
        verbose_name=_("grouping order"),
        help_text=_(
            "Sometimes the parent_tag relationship by itself is not enough to convey "
            "full information about the information hierarchy.<br>"
            "Some categories are broader, and others are more specific. More specific "
            "tags should probably be visually grouped after/under broader tags when "
            "displayed.<br>The broader the category is the lower grouping order it "
            "should have - e.g. 'year' should have lower order than 'round'.<br>"
            "Left blank means 'infinity', which usually means that this category will "
            "not be used for grouping - some categories could be too specific (e.g. "
            "when grouping would result in 'groups' of single Problems)."
        ),
    )

    class Meta(object):
        verbose_name = _("origin tag - information category")
        verbose_name_plural = _("origin tags - information categories")
        unique_together = ('name', 'parent_tag')

    def __str__(self):
        return str("{}_{}".format(self.parent_tag, self.name))



class OriginInfoCategoryLocalization(models.Model):
    origin_info_category = models.ForeignKey(
        OriginInfoCategory, related_name='localizations', on_delete=models.CASCADE
    )
    language = models.CharField(
        max_length=2, choices=settings.LANGUAGES, verbose_name=_("language")
    )
    full_name = models.CharField(
        max_length=32,
        verbose_name=_("name translation"),
        help_text=_("Human-readable name."),
    )

    class Meta(object):
        unique_together = ('origin_info_category', 'language')
        verbose_name = _("origin info category localization")
        verbose_name_plural = _("origin info category localizations")

    def __str__(self):
        return str("{} - {}".format(self.origin_info_category, self.language))


@_localized('full_value')

class OriginInfoValue(models.Model):
    """This class represents additional information, further specifying
    what its parent_tag is already telling about the origin. Each
    OriginInfoValue has a category, in which it should be unique, and
    problems should only have one OriginInfoValue within any category.

    See alse: OriginTag, OriginInfoCategory
    """

    parent_tag = models.ForeignKey(
        OriginTag,
        related_name='info_values',
        on_delete=models.CASCADE,
        verbose_name=_("parent tag"),
        help_text=_(
            "If an OriginTag T is a parent of OriginInfoValue V, the presence of V "
            "on a Problem implies the presence of T.<br>"
            "OriginInfoValues with the same values are also treated as distinct if "
            "they have different parents.<br>"
            "You can think of this distinction as prepending an OriginTag.name prefix "
            "to an OriginInfoValue.value<br>"
            "e.g. for OriginTag 'pa' and OriginInfoValue '2011', this unique "
            "OriginInfoValue.name would be 'pa_2011'"
        ),
    )
    category = models.ForeignKey(
        OriginInfoCategory,
        related_name='values',
        on_delete=models.CASCADE,
        verbose_name=_("category"),
        help_text=_(
            "This information should be categorized under the selected category."
        ),
    )
    value = models.CharField(
        max_length=32,
        validators=(validate_origintag,),
        verbose_name=_("value"),
        help_text=_(
            "Short, searchable value consisting of only lowercase letters and "
            "numbers.<br>"
            "This will be displayed verbatim in the Problemset - it must be unique "
            "within its parent tag.<br>"
            "Examples: for year: '2011', but for round: 'r1' (just '1' for round "
            "would be ambiguous)."
        ),
    )
    order = models.IntegerField(
        default=0,
        verbose_name=_("display order"),
        help_text=_("Order in which this value will be sorted within its category."),
    )
    problems = models.ManyToManyField(
        Problem,
        blank=True,
        verbose_name=_("problems"),
        help_text=_(
            "Select problems described by this value. They will also be tagged with "
            "the parent tag.<br>"
        ),
    )

    @property
    def name(self):
        # Should be unique due to unique constraints on value and parent_tag.name
        return str('{}_{}'.format(self.parent_tag, self.value))

    @property
    def full_name(self):
        return str(
            u'{} {}'.format(self.parent_tag.full_name, self.full_value)
        )

    class Meta(object):
        unique_together = ('parent_tag', 'value')
        verbose_name = _("origin tag - information value")
        verbose_name_plural = _("origin tags - information values")

    def __str__(self):
        return str(self.name)



class OriginInfoValueLocalization(models.Model):
    origin_info_value = models.ForeignKey(
        OriginInfoValue, related_name='localizations', on_delete=models.CASCADE
    )
    language = models.CharField(
        max_length=2, choices=settings.LANGUAGES, verbose_name=_("language")
    )
    full_value = models.CharField(
        max_length=64,
        verbose_name=_("translated value"),
        help_text=_("Human-readable value."),
    )

    class Meta(object):
        unique_together = ('origin_info_value', 'language')
        verbose_name = _("origin info value localization")
        verbose_name_plural = _("origin info value localizations")

    def __str__(self):
        return str("{} - {}".format(self.origin_info_value, self.language))


@_localized('full_name')

class DifficultyTag(models.Model):
    name = models.CharField(
        max_length=20,
        unique=True,
        verbose_name=_("name"),
        null=False,
        blank=False,
        validators=[
            validators.MinLengthValidator(3),
            validators.MaxLengthValidator(20),
            validators.validate_slug,
        ],
    )
    problems = models.ManyToManyField(Problem, through='DifficultyTagThrough')

    class Meta(object):
        verbose_name = _("difficulty tag")
        verbose_name_plural = _("difficulty tags")

    def __str__(self):
        return str(self.name)



class DifficultyTagThrough(models.Model):
    problem = models.OneToOneField(Problem, on_delete=models.CASCADE)
    tag = models.ForeignKey(DifficultyTag, on_delete=models.CASCADE)

    # This string will be visible in an admin form.
    def __str__(self):
        return str(self.tag.name)



class DifficultyTagLocalization(models.Model):
    difficulty_tag = models.ForeignKey(
        DifficultyTag, related_name='localizations', on_delete=models.CASCADE
    )
    language = models.CharField(
        max_length=2, choices=settings.LANGUAGES, verbose_name=_("language")
    )
    full_name = models.CharField(
        max_length=32,
        verbose_name=_("name translation"),
        help_text=_("Human-readable name."),
    )

    class Meta(object):
        unique_together = ('difficulty_tag', 'language')
        verbose_name = _("difficulty tag localization")
        verbose_name_plural = _("difficulty tag localizations")

    def __str__(self):
        return str("{} - {}".format(self.difficulty_tag, self.language))



class DifficultyTagProposal(models.Model):
    problem = models.ForeignKey(Problem, on_delete=models.CASCADE)
    tag = models.ForeignKey(DifficultyTag, on_delete=models.CASCADE, null=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)

    def __str__(self):
        return str(self.problem.name) + u' -- ' + str(self.tag.name)

    class Meta(object):
        verbose_name = _("difficulty proposal")
        verbose_name_plural = _("difficulty proposals")


@_localized('full_name')

class AlgorithmTag(models.Model):
    name = models.CharField(
        max_length=20,
        unique=True,
        verbose_name=_("name"),
        null=False,
        blank=False,
        validators=[
            validators.MinLengthValidator(2),
            validators.MaxLengthValidator(20),
            validators.validate_slug,
        ],
    )
    problems = models.ManyToManyField(Problem, through='AlgorithmTagThrough')

    class Meta(object):
        verbose_name = _("algorithm tag")
        verbose_name_plural = _("algorithm tags")

    def __str__(self):
        return str(self.name)



class AlgorithmTagThrough(models.Model):
    problem = models.ForeignKey(Problem, on_delete=models.CASCADE)
    tag = models.ForeignKey(AlgorithmTag, on_delete=models.CASCADE)

    # This string will be visible in an admin form.
    def __str__(self):
        return str(self.tag.name)

    class Meta(object):
        unique_together = ('problem', 'tag')



class AlgorithmTagLocalization(models.Model):
    algorithm_tag = models.ForeignKey(
        AlgorithmTag, related_name='localizations', on_delete=models.CASCADE
    )
    language = models.CharField(
        max_length=2, choices=settings.LANGUAGES, verbose_name=_("language")
    )
    full_name = models.CharField(
        max_length=50,
        verbose_name=_("name translation"),
        help_text=_("Human-readable name."),
    )

    class Meta(object):
        unique_together = ('algorithm_tag', 'language')
        verbose_name = _("algorithm tag localization")
        verbose_name_plural = _("algorithm tag localizations")

    def __str__(self):
        return str("{} - {}".format(self.algorithm_tag, self.language))



class AlgorithmTagProposal(models.Model):
    problem = models.ForeignKey(Problem, on_delete=models.CASCADE)
    tag = models.ForeignKey(AlgorithmTag, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)

    def __str__(self):
        return str(self.problem.name) + u' -- ' + str(self.tag.name)

    class Meta(object):
        verbose_name = _("algorithm tag proposal")
        verbose_name_plural = _("algorithm tag proposals")
