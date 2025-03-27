import itertools
import os.path

from django.conf import settings
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Max
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone

from django.utils.module_loading import import_string
from django.utils.text import get_valid_filename
from django.utils.translation import gettext_lazy as _
from django.utils.translation import ngettext

from oioioi.base.fields import DottedNameField, EnumField, EnumRegistry
from oioioi.base.menu import MenuItem, menu_registry
from oioioi.base.utils import strip_num_or_hash
from oioioi.base.utils.validators import validate_db_string_id, validate_whitespaces
from oioioi.contests.date_registration import date_registry
from oioioi.contests.fields import ScoreField
from oioioi.contests.problem_instance_controller import ProblemInstanceController
from oioioi.filetracker.fields import FileField
from enum import Enum


def make_contest_filename(instance, filename):
    if not isinstance(instance, Contest):
        assert hasattr(instance, 'contest'), (
            'contest_file_generator used '
            'on object %r which does not have \'contest\' attribute' % (instance,)
        )
        instance = getattr(instance, 'contest')
    return 'contests/%s/%s' % (
        instance.id,
        get_valid_filename(os.path.basename(filename)),
    )


class Contest(models.Model):
    id = models.CharField(
        max_length=32,
        primary_key=True,
        verbose_name=_("ID"),
        validators=[validate_db_string_id],
    )
    name = models.CharField(
        max_length=255, verbose_name=_("full name"), validators=[validate_whitespaces]
    )
    # The controller_name field is deliberately lacking default value. This
    # ensures that the contest type is explicitly set when persisting
    # an object to the database.
    controller_name = DottedNameField(
        'oioioi.contests.controllers.ContestController', verbose_name=_("type")
    )
    creation_date = models.DateTimeField(
        auto_now_add=True,
        editable=False,
        db_index=True,
        verbose_name=_("creation date"),
    )
    default_submissions_limit = models.IntegerField(
        verbose_name=_("default submissions limit"),
        help_text=_("Use 0 for unlimited submissions."),
        default=settings.DEFAULT_SUBMISSIONS_LIMIT,
        blank=True,
    )
    contact_email = models.EmailField(
        blank=True,
        verbose_name=_("contact email"),
        help_text=_(
            "Address of contest owners. Sent emails related "
            "to this contest (i.e. submission confirmations) "
            "will have the return address set to this value. "
            "Defaults to system admins address if left empty."
        ),
    )
    judging_priority = models.IntegerField(
        verbose_name=_("judging priority"),
        default=settings.DEFAULT_CONTEST_PRIORITY,
        help_text=_(
            "Contest with higher judging priority is always judged "
            "before contest with lower judging priority."
        ),
    )
    judging_weight = models.IntegerField(
        verbose_name=_("judging weight"),
        default=settings.DEFAULT_CONTEST_WEIGHT,
        validators=[MinValueValidator(1)],
        help_text=_(
            "If some contests have the same judging priority, the "
            "judging resources are allocated proportionally to "
            "their weights."
        ),
    )
    enable_editor = models.BooleanField(
        verbose_name=_("enable editor"),
        default=False
    )
    show_contest_rules = models.BooleanField(
        verbose_name=_("show contest rules"),
        default=True
    )
    is_archived = models.BooleanField(
        verbose_name=_("is archived"),
        default=False
    )
    school_year = models.CharField(
        max_length=10, verbose_name=_("school year"),  default=""
    )

    # Part of szkopul backporting.
    # This is a hack for situation where contest controller is empty,
    # which is very uncommon in normal usage.
    def save(self, *args, **kwargs):
        if not self.controller_name:
            self.controller_name = 'oioioi.teachers.controllers.TeacherContestController'
        super(Contest, self).save(*args, **kwargs)

    @property
    def controller(self):
        if not self.controller_name:
            return None
        return import_string(self.controller_name)(self)

    class Meta(object):
        verbose_name = _("contest")
        verbose_name_plural = _("contests")
        get_latest_by = 'creation_date'
        permissions = (
            ('contest_admin', _("Can administer the contest")),
            ('contest_observer', _("Can observe the contest")),
            ('enter_contest', _("Can enter the contest")),
            ('personal_data', _("Has access to the private data of users")),
        )

    def __str__(self):
        return str(self.name)


@receiver(pre_save, sender=Contest)
def _generate_contest_id(sender, instance, raw, **kwargs):
    """Automatically generate a contest ID if not provided, by trying ``p0``,
    ``p1``, etc."""
    if not raw and not instance.id:
        instance_ids = frozenset(Contest.objects.values_list('id', flat=True))
        for i in itertools.count(1):
            candidate = 'c' + str(i)
            if candidate not in instance_ids:
                instance.id = candidate
                break


@receiver(post_save, sender=Contest)
def _call_controller_adjust_contest(sender, instance, raw, **kwargs):
    if not raw and instance.controller_name:
        instance.controller.adjust_contest()


class ContestAttachment(models.Model):
    """Represents an additional file visible to the contestant, linked to
    the contest or to the round.

    This may be used for additional materials, like rules, documentation
    etc.
    """

    contest = models.ForeignKey(
        Contest,
        related_name='c_attachments',
        verbose_name=_("contest"),
        on_delete=models.CASCADE,
    )
    description = models.CharField(max_length=255, verbose_name=_("description"))
    content = FileField(upload_to=make_contest_filename, verbose_name=_("content"))
    round = models.ForeignKey(
        'Round',
        related_name='r_attachments',
        blank=True,
        null=True,
        verbose_name=_("round"),
        on_delete=models.CASCADE,
    )
    pub_date = models.DateTimeField(
        default=None, blank=True, null=True, verbose_name=_("publication date")
    )

    @property
    def filename(self):
        return os.path.split(self.content.name)[1]

    @property
    def download_name(self):
        return strip_num_or_hash(self.filename)

    def __str__(self):
        return str(self.filename)

    class Meta(object):
        verbose_name = _("attachment")
        verbose_name_plural = _("attachments")


def _round_end_date_name_generator(obj):
    max_round_extension = RoundTimeExtension.objects.filter(round=obj).aggregate(
        Max('extra_time')
    )['extra_time__max']
    if max_round_extension is not None:
        text = ngettext(
            "End of %(name)s (+ %(ext)d min)",
            "End of %(name)s (+ %(ext)d mins)",
            max_round_extension,
        )
        text = text % {'name': obj.name, 'ext': max_round_extension}
        return text
    else:
        return _("End of %s") % obj.name


@date_registry.register(
    'start_date',
    name_generator=(lambda obj: _("Start of %s") % obj.name),
    round_chooser=(lambda obj: obj),
    order=0,
)
@date_registry.register(
    'end_date',
    name_generator=_round_end_date_name_generator,
    round_chooser=(lambda obj: obj),
    order=1,
)
@date_registry.register(
    'results_date',
    name_generator=(lambda obj: _("Results of %s") % obj.name),
    round_chooser=(lambda obj: obj),
    order=30,
)
@date_registry.register(
    'public_results_date',
    name_generator=(lambda obj: _("Public results of %s") % obj.name),
    round_chooser=(lambda obj: obj),
    order=31,
)
class Round(models.Model):
    contest = models.ForeignKey(
        Contest, verbose_name=_("contest"), on_delete=models.CASCADE
    )
    name = models.CharField(
        max_length=255, verbose_name=_("name"), validators=[validate_whitespaces]
    )
    start_date = models.DateTimeField(
        default=timezone.now, verbose_name=_("start date")
    )
    end_date = models.DateTimeField(blank=True, null=True, verbose_name=_("end date"))
    results_date = models.DateTimeField(
        blank=True, null=True, verbose_name=_("results date")
    )
    public_results_date = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name=_("public results date"),
        help_text=_(
            "Participants may learn about others' results, "
            "what exactly happens depends on the type of the contest "
            "(eg. rankings, contestants' solutions are published)."
        ),
    )
    is_trial = models.BooleanField(default=False, verbose_name=_("is trial"))

    class Meta(object):
        verbose_name = _("round")
        verbose_name_plural = _("rounds")
        unique_together = ('contest', 'name')
        ordering = ('contest', 'start_date')

    def __str__(self):
        return str(self.name)

    def clean(self):
        if self.start_date and self.end_date and self.start_date > self.end_date:
            raise ValidationError(_("Start date should be before end date."))
        if self.public_results_date:
            if self.results_date is None:
                raise ValidationError(
                    _(
                        "If you specify a public results "
                        "date, you should enter a results date too."
                    )
                )
            if self.results_date > self.public_results_date:
                raise ValidationError(
                    _("Results cannot appear later than public results.")
                )


@receiver(pre_save, sender=Round)
def _generate_round_id(sender, instance, raw, **kwargs):
    """Automatically generate a round name if not provided."""
    if not raw and not instance.name:
        num_other_rounds = (
            Round.objects.filter(contest=instance.contest)
            .exclude(pk=instance.pk)
            .count()
        )
        instance.name = _("Round %d") % (num_other_rounds + 1,)


statements_visibility_options = EnumRegistry()
statements_visibility_options.register('YES', _("Visible"))
statements_visibility_options.register('NO', _("Not visible"))
statements_visibility_options.register('AUTO', _("Auto"))


class ProblemStatementConfig(models.Model):
    contest = models.OneToOneField('contests.Contest', on_delete=models.CASCADE)
    visible = EnumField(
        statements_visibility_options,
        default='AUTO',
        verbose_name=_("statements visibility"),
        help_text=_(
            "If set to Auto, the visibility is determined "
            "according to the type of the contest."
        ),
    )

    class Meta(object):
        verbose_name = _("problem statement config")
        verbose_name_plural = _("problem statement configs")


ranking_visibility_options = EnumRegistry()
ranking_visibility_options.register('YES', _("Visible"))
ranking_visibility_options.register('NO', _("Not visible"))
ranking_visibility_options.register('AUTO', _("Auto"))


class RankingVisibilityConfig(models.Model):
    contest = models.OneToOneField('contests.Contest', on_delete=models.CASCADE)
    visible = EnumField(
        ranking_visibility_options,
        default='AUTO',
        verbose_name=_("ranking visibility"),
        help_text=_(
            "If set to Auto, the visibility is determined "
            "according to the type of the contest.\n"
            "Until the date of publication of the results, "
            "the ranking is visible only to administrators."
        ),
    )

    class Meta(object):
        verbose_name = _("ranking visibility config")
        verbose_name_plural = _("ranking visibility configs")


registration_availability_options = EnumRegistry()
registration_availability_options.register('YES', _("Open"))
registration_availability_options.register('NO', _("Closed"))
registration_availability_options.register('CONFIG', _("Configuration"))

class RegistrationStatus(Enum):
    OPEN = 1
    CLOSED = 2
    NOT_OPEN_YET = 3

@date_registry.register(
    'registration_available_from', name_generator=(lambda obj: _("Make registration available"))
)
@date_registry.register(
    'registration_available_to', name_generator=(lambda obj: _("Make registration unavailable"))
)
class RegistrationAvailabilityConfig(models.Model):
    contest = models.OneToOneField('contests.Contest', on_delete=models.CASCADE)
    enabled = EnumField(
        registration_availability_options,
        default='YES',
        verbose_name=_("Registration vailability"),
        help_text=_(
            "If set to Open, the registration will be opened always."
            "If set to Closed, the registration will be closed always."
            "If set to Configuration, the registration will be opened "
            "according to the following settings."
        ),
    )
    registration_available_from = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name=_("available from"),
        help_text=_(
            "If set, the registration will be opened automatically at the specified date."
        ),
    )
    registration_available_to = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name=_("available to"),
        help_text=_(
            "If set, the registration will be closed automatically at the specified date."
        ),
    )

    class Meta(object):
        verbose_name = _("Registration availability config")
        verbose_name_plural = _("open registration configs")

    def is_registration_open(self, timestamp):
        if self.enabled == 'YES':
            return True
        if self.enabled == 'CONFIG':
            return self.registration_available_from <= timestamp <= self.registration_available_to
        return False


    def registration_status(self, timestamp):
        if self.enabled == 'YES':
            return RegistrationStatus.OPEN
        if self.enabled == 'CONFIG':
            if self.registration_available_from <= timestamp <= self.registration_available_to:
                return RegistrationStatus.OPEN
            elif self.registration_available_to < timestamp:
                return RegistrationStatus.CLOSED
            elif timestamp < self.registration_available_to:
                return RegistrationStatus.NOT_OPEN_YET
        return RegistrationStatus.CLOSED

    def clean(self):
        if self.enabled == 'CONFIG':
            if self.registration_available_from is None or self.registration_available_to is None:
                raise ValidationError(_("If registration availability is set to Configuration, then "
                                        "'Available from' and 'Available to' must be set."))
            if self.registration_available_from > self.registration_available_to:
                raise ValidationError(_("'Available from' must be before 'available to'."))


class ProblemInstance(models.Model):
    contest = models.ForeignKey(
        Contest,
        verbose_name=_("contest"),
        null=True,
        blank=True,
        on_delete=models.CASCADE,
    )
    round = models.ForeignKey(
        Round, verbose_name=_("round"), null=True, blank=True, on_delete=models.CASCADE
    )
    problem = models.ForeignKey(
        'problems.Problem', verbose_name=_("problem"), on_delete=models.CASCADE
    )
    short_name = models.CharField(
        max_length=30, verbose_name=_("short name"), validators=[validate_db_string_id]
    )
    submissions_limit = models.IntegerField(
        default=settings.DEFAULT_SUBMISSIONS_LIMIT,
        help_text=_("Use 0 for unlimited submissions."),
        verbose_name=_("submissions limit"),
    )

    # set on True only when problem_instace's tests were overriden but there
    # are some submissions judged on old tests
    needs_rejudge = models.BooleanField(default=False, verbose_name=_("needs rejudge"))

    class Meta(object):
        verbose_name = _("problem instance")
        verbose_name_plural = _("problem instances")
        unique_together = ('contest', 'short_name')
        ordering = ('round', 'short_name')

    def get_short_name_display(self):
        problem_short_name = self.problem.short_name
        if problem_short_name.lower() == self.short_name:
            return problem_short_name
        else:
            return self.short_name

    def __str__(self):
        return u'{} ({})'.format(self.problem.name, self.get_short_name_display())

    @property
    def controller(self):
        return ProblemInstanceController(self)


@receiver(pre_save, sender=ProblemInstance)
def _generate_problem_instance_fields(sender, instance, raw, **kwargs):
    if not raw and instance.round_id:
        instance.contest = instance.round.contest
    if not raw and not instance.short_name and instance.problem_id:
        if instance.contest:
            short_names = ProblemInstance.objects.filter(
                contest=instance.contest
            ).values_list('short_name', flat=True)
        else:
            short_names = ProblemInstance.objects.filter(
                contest__isnull=True
            ).values_list('short_name', flat=True)
        # SlugField and validate_slug accepts uppercase letters, while we don't
        problem_short_name = instance.problem.short_name.lower()
        if problem_short_name not in short_names:
            instance.short_name = problem_short_name
        else:
            for i in itertools.count(1):
                candidate = problem_short_name + str(i)
                if candidate not in short_names:
                    instance.short_name = candidate
                    break


submission_kinds = EnumRegistry()
submission_kinds.register('NORMAL', _("Normal"))
#: Like NORMAL, but score has no effect on anything
submission_kinds.register('IGNORED', _("Ignored"))
#: Won't be graded unless approved by admin
submission_kinds.register('SUSPECTED', _("Suspected"))
#: Like IGNORED, but user shall not see it anymore
submission_kinds.register('IGNORED_HIDDEN', _("Ignored-Hidden"))

submission_statuses = EnumRegistry()
submission_statuses.register('?', _("Pending"))
submission_statuses.register('OK', _("OK"))
submission_statuses.register('ERR', _("Error"))


class Submission(models.Model):
    problem_instance = models.ForeignKey(
        ProblemInstance, verbose_name=_("problem"), on_delete=models.CASCADE
    )
    user = models.ForeignKey(
        User, blank=True, null=True, verbose_name=_("user"), on_delete=models.CASCADE
    )
    date = models.DateTimeField(
        default=timezone.now, blank=True, verbose_name=_("date"), db_index=True
    )
    kind = EnumField(submission_kinds, default='NORMAL', verbose_name=_("kind"))
    score = ScoreField(blank=True, null=True, verbose_name=_("score"))
    status = EnumField(submission_statuses, default='?', verbose_name=_("status"))
    comment = models.TextField(blank=True, verbose_name=_("comment"))

    @property
    def problem(self):
        return self.problem_instance.problem

    class Meta(object):
        verbose_name = _("submission")
        verbose_name_plural = _("submissions")
        get_latest_by = 'date'

    def is_scored(self):
        return self.score is not None

    def get_date_display(self, shortened=False):
        return self.problem_instance.controller.render_submission_date(self, shortened)

    def get_date_display_shortened(self):
        return self.get_date_display(True)

    def get_score_display(self):
        if self.score is None:
            return None
        return self.problem_instance.controller.render_submission_score(self)

    def __str__(self):
        return u"Submission(%d, %s, %s, %s, %s, %s)" % (
            self.id,
            self.problem_instance.problem.name,
            self.user.username if self.user else None,
            self.date,
            self.kind,
            self.status,
        )


submission_report_kinds = EnumRegistry()
submission_report_kinds.register('FINAL', _("Final report"))
submission_report_kinds.register('FAILURE', _("Evaluation failure report"))

submission_report_statuses = EnumRegistry()
submission_report_statuses.register('INACTIVE', _("Inactive"))
submission_report_statuses.register('ACTIVE', _("Active"))
submission_report_statuses.register('SUPERSEDED', _("Superseded"))


class SubmissionReport(models.Model):
    submission = models.ForeignKey(Submission, on_delete=models.CASCADE)
    creation_date = models.DateTimeField(auto_now_add=True)
    kind = EnumField(submission_report_kinds, default='FINAL')
    status = EnumField(submission_report_statuses, default='INACTIVE')

    @property
    def score_report(self):
        try:
            return self.scorereport_set.all()[0]
        except (ScoreReport.DoesNotExist, IndexError):
            return None

    class Meta(object):
        get_latest_by = 'creation_date'
        ordering = ('-creation_date',)
        index_together = (('submission', 'creation_date'),)


class ScoreReport(models.Model):
    submission_report = models.ForeignKey(SubmissionReport, on_delete=models.CASCADE)
    status = EnumField(submission_statuses, blank=True, null=True)
    score = ScoreField(blank=True, null=True)
    max_score = ScoreField(blank=True, null=True)
    comment = models.TextField(blank=True, null=True)

    def get_score_display(self):
        if self.score is None:
            return ''
        return str(self.score)


class FailureReport(models.Model):
    """A report generated when evaluation process failed.

    The submission should have its status set to ``FAILED``. Such reports
    are not shown to users.
    """

    submission_report = models.ForeignKey(SubmissionReport, on_delete=models.CASCADE)
    message = models.TextField()
    json_environ = models.TextField()


class UserResultForProblem(models.Model):
    """User result (score) for the problem.

    Each user can have only one class:`UserResultForProblem` per problem
    instance.
    """

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    problem_instance = models.ForeignKey(ProblemInstance, on_delete=models.CASCADE)
    score = ScoreField(blank=True, null=True)
    status = EnumField(submission_statuses, blank=True, null=True)
    submission_report = models.ForeignKey(
        SubmissionReport, blank=True, null=True, on_delete=models.CASCADE
    )

    class Meta(object):
        unique_together = ('user', 'problem_instance')


class UserResultForRound(models.Model):
    """User result (score) for the round.

    Each user can have only one :class:`UserResultForRound` per round.
    """

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    round = models.ForeignKey(Round, on_delete=models.CASCADE)
    score = ScoreField(blank=True, null=True)

    class Meta(object):
        unique_together = ('user', 'round')


class UserResultForContest(models.Model):
    """Represents the user result (score) for the contest.

    Each user can have only one :class:`UserResultForContest` per contest
    for given type.
    """

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    contest = models.ForeignKey(Contest, on_delete=models.CASCADE)
    score = ScoreField(blank=True, null=True)

    class Meta(object):
        unique_together = ('user', 'contest')


class RoundTimeExtension(models.Model):
    """Represents the time the round has been extended by for a certain user.

    The extra time is given in minutes.
    """

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    round = models.ForeignKey(Round, on_delete=models.CASCADE)
    extra_time = models.PositiveIntegerField(_("Extra time (in minutes)"))

    class Meta(object):
        unique_together = ('user', 'round')
        verbose_name = _("round time extension")
        verbose_name_plural = _("round time extensions")

    def __str__(self):
        return str(self.round) + u': ' + str(self.user)


contest_permissions = EnumRegistry()
contest_permissions.register('contests.contest_owner', _("Owner"))
contest_permissions.register('contests.contest_admin', _("Admin"))
contest_permissions.register('contests.contest_basicadmin', _("Basic Admin"))
contest_permissions.register('contests.contest_observer', _("Observer"))
contest_permissions.register('contests.personal_data', _("Personal Data"))


class ContestPermission(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    contest = models.ForeignKey(Contest, on_delete=models.CASCADE)
    permission = EnumField(
        contest_permissions,
        default='contests.contest_admin',
        verbose_name=_("permission"),
    )

    class Meta(object):
        unique_together = ('user', 'contest', 'permission')
        verbose_name = _("contest permission")
        verbose_name_plural = _("contest permissions")

    def __str__(self):
        return u'%s/%s: %s' % (self.contest, self.permission, self.user)


class ContestView(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    contest = models.ForeignKey(Contest, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(default=timezone.now, verbose_name=_("last view"))

    class Meta(object):
        unique_together = ('user', 'contest')
        index_together = [['user', 'timestamp']]
        get_latest_by = 'timestamp'
        ordering = ('-timestamp',)

    def __str__(self):
        return u'%s,%s' % (self.user, self.contest)


class ContestLink(models.Model):
    contest = models.ForeignKey(
        Contest, verbose_name=_("contest"), on_delete=models.CASCADE
    )
    description = models.CharField(max_length=255, verbose_name=_("description"))
    url = models.URLField(verbose_name=_("url"))
    order = models.IntegerField(blank=True, null=True)

    class Meta(object):
        verbose_name = _("contest menu link")
        verbose_name_plural = _("contest menu links")


def contest_links_generator(request):
    if not hasattr(request, 'contest'):
        return

    links = ContestLink.objects.filter(contest=request.contest)
    for link in links:
        # pylint: disable=cell-var-from-loop
        # http://docs.python-guide.org/en/latest/writing/gotchas/#late-binding-closures
        url_generator = lambda request, url=link.url: url
        item = MenuItem(
            name='contest_link_%d' % link.id,
            text=link.description,
            url_generator=url_generator,
            order=link.order,
        )
        yield item


menu_registry.register_generator('contest_links', contest_links_generator)


class FilesMessage(models.Model):
    contest = models.OneToOneField(Contest, primary_key=True, on_delete=models.CASCADE)
    content = models.TextField(verbose_name=_("message"), blank=True)

    class Meta(object):
        verbose_name = _("files message")
        verbose_name_plural = _("files messages")


class SubmissionsMessage(models.Model):
    contest = models.OneToOneField(Contest, primary_key=True, on_delete=models.CASCADE)
    content = models.TextField(verbose_name=_("message"), blank=True)

    class Meta(object):
        verbose_name = _("submissions message")
        verbose_name_plural = _("submissions messages")


class SubmitMessage(models.Model):
    contest = models.OneToOneField(Contest, primary_key=True, on_delete=models.CASCADE)
    content = models.TextField(verbose_name=_("message"), blank=True)

    class Meta(object):
        verbose_name = _("new submission message")
        verbose_name_plural = _("new submission messages")

class SubmissionMessage(models.Model):
    contest = models.OneToOneField(Contest, primary_key=True, on_delete=models.CASCADE)
    content = models.TextField(verbose_name=_("message"), blank=True)

    class Meta(object):
        verbose_name = _("submission message")
        verbose_name_plural = _("submission messages")
