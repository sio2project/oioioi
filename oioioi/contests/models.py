import itertools
import os.path

from django.conf import settings
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Max
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from django.utils import timezone
from django.utils.text import get_valid_filename
from django.utils.translation import ugettext_lazy as _, ungettext

from oioioi.base.fields import DottedNameField, EnumRegistry, EnumField
from oioioi.base.menu import menu_registry, MenuItem
from oioioi.base.utils import get_object_by_dotted_name
from oioioi.contests.fields import ScoreField
from oioioi.filetracker.fields import FileField
from oioioi.base.utils.validators import validate_whitespaces, \
        validate_db_string_id
from oioioi.problems.models import Problem
from oioioi.contests.date_registration import date_registry


def make_contest_filename(instance, filename):
    if not isinstance(instance, Contest):
        assert hasattr(instance, 'contest'), 'contest_file_generator used ' \
                'on object %r which does not have \'contest\' attribute' \
                % (instance,)
        instance = getattr(instance, 'contest')
    return 'contests/%s/%s' % (instance.id,
            get_valid_filename(os.path.basename(filename)))


class Contest(models.Model):
    id = models.CharField(max_length=32, primary_key=True,
            verbose_name=_("ID"), validators=[validate_db_string_id])
    name = models.CharField(max_length=255, verbose_name=_("full name"),
                            validators=[validate_whitespaces])
    controller_name = DottedNameField(
            'oioioi.contests.controllers.ContestController',
            verbose_name=_("type"))
    creation_date = models.DateTimeField(auto_now_add=True, editable=False,
            db_index=True, verbose_name=_("creation date"))
    default_submissions_limit = models.IntegerField(
            verbose_name=_("default submissions limit"),
            default=settings.DEFAULT_SUBMISSIONS_LIMIT, blank=True)
    contact_email = models.EmailField(blank=True,
            verbose_name=_("contact email"),
            help_text=_("Address of contest owners. Sent emails related "
                "to this contest (i.e. submission confirmations) "
                "will have the return address set to this value. "
                "Defaults to system admins address if left empty."))

    @property
    def controller(self):
        if not self.controller_name:
            return None
        return get_object_by_dotted_name(self.controller_name)(self)

    class Meta(object):
        verbose_name = _("contest")
        verbose_name_plural = _("contests")
        get_latest_by = 'creation_date'
        permissions = (
            ('contest_admin', _("Can administer the contest")),
            ('contest_observer', _("Can observe the contest")),
            ('enter_contest', _("Can enter the contest")),
            ('personal_data', _("Has access to the private data of users"))
        )

    def __unicode__(self):
        return self.name


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
    contest = models.ForeignKey(Contest, related_name='c_attachments',
            verbose_name=_("contest"))
    description = models.CharField(max_length=255,
            verbose_name=_("description"))
    content = FileField(upload_to=make_contest_filename,
            verbose_name=_("content"))
    round = models.ForeignKey('Round', related_name='r_attachments',
            blank=True, null=True, verbose_name=_("round"))

    @property
    def filename(self):
        return os.path.split(self.content.name)[1]

    class Meta(object):
        verbose_name = _("attachment")
        verbose_name_plural = _("attachments")


def _round_end_date_name_generator(obj):
    max_round_extension = RoundTimeExtension.objects.filter(round=obj). \
            aggregate(Max('extra_time'))['extra_time__max']
    if max_round_extension is not None:
        return ungettext("End of %(name)s (+ %(ext)d min)",
                         "End of %(name)s (+ %(ext)d mins)",
                         max_round_extension) % \
                         {'name': obj.name, 'ext': max_round_extension}
    else:
        return _("End of %s") % obj.name


@date_registry.register('start_date',
                        name_generator=(lambda obj:
                                        _("Start of %s") % obj.name),
                        round_chooser=(lambda obj: obj),
                        order=0)
@date_registry.register('end_date',
                        name_generator=_round_end_date_name_generator,
                        round_chooser=(lambda obj: obj),
                        order=1)
@date_registry.register('results_date',
                        name_generator=(lambda obj:
                                        _("Results of %s") % obj.name),
                        round_chooser=(lambda obj: obj),
                        order=30)
@date_registry.register('public_results_date',
                        name_generator=(lambda obj:
                                        _("Public results of %s") % obj.name),
                        round_chooser=(lambda obj: obj),
                        order=31)
class Round(models.Model):
    contest = models.ForeignKey(Contest, verbose_name=_("contest"))
    name = models.CharField(max_length=255, verbose_name=_("name"),
                            validators=[validate_whitespaces])
    start_date = models.DateTimeField(default=timezone.now,
            verbose_name=_("start date"))
    end_date = models.DateTimeField(blank=True, null=True,
            verbose_name=_("end date"))
    results_date = models.DateTimeField(blank=True, null=True,
            verbose_name=_("results date"))
    public_results_date = models.DateTimeField(blank=True, null=True,
            verbose_name=_("public results date"),
            help_text=_("Participants may learn about others' results, "
                "what exactly happens depends on the type of the contest "
                "(eg. rankings, contestants' solutions are published)."))
    is_trial = models.BooleanField(default=False, verbose_name=_("is trial"))

    class Meta(object):
        verbose_name = _("round")
        verbose_name_plural = _("rounds")
        unique_together = ('contest', 'name')
        ordering = ('contest', 'start_date')

    def __unicode__(self):
        return self.name

    def clean(self):
        if self.start_date and self.end_date and \
                self.start_date > self.end_date:
            raise ValidationError(_("Start date should be before end date."))
        if self.public_results_date:
            if self.results_date is None:
                raise ValidationError(_("If you specify a public results "
                    "date, you should enter a results date too."))
            if self.results_date > self.public_results_date:
                raise ValidationError(_("Results cannot appear later than "
                    "public results."))


@receiver(pre_save, sender=Round)
def _generate_round_id(sender, instance, raw, **kwargs):
    """Automatically generate a round name if not provided."""
    if not raw and not instance.name:
        num_other_rounds = Round.objects.filter(contest=instance.contest) \
                .exclude(pk=instance.pk).count()
        instance.name = _("Round %d") % (num_other_rounds + 1,)

statements_visibility_options = EnumRegistry()
statements_visibility_options.register('YES', _("Visible"))
statements_visibility_options.register('NO', _("Not visible"))
statements_visibility_options.register('AUTO', _("Auto"))


class ProblemStatementConfig(models.Model):
    contest = models.OneToOneField('contests.Contest')
    visible = EnumField(statements_visibility_options, default='AUTO',
            verbose_name=_("statements visibility"),
            help_text=_("If set to Auto, the visibility is determined "
                "according to the type of the contest."))

    class Meta(object):
        verbose_name = _("problem statement config")
        verbose_name_plural = _("problem statement configs")


class ProblemInstance(models.Model):
    contest = models.ForeignKey(Contest, verbose_name=_("contest"))
    round = models.ForeignKey(Round, verbose_name=_("round"), null=True,
            blank=True)
    problem = models.ForeignKey(Problem, verbose_name=_("problem"))
    short_name = models.CharField(max_length=30, verbose_name=_("short name"),
            validators=[validate_db_string_id])
    submissions_limit = models.IntegerField(blank=True,
        default=settings.DEFAULT_SUBMISSIONS_LIMIT,
        verbose_name=_("submissions limit"))

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

    def __unicode__(self):
        return '%(name)s (%(short_name)s)' % {
            'short_name': self.get_short_name_display(),
            'name': self.problem.name,
        }


@receiver(pre_save, sender=ProblemInstance)
def _generate_problem_instance_fields(sender, instance, raw, **kwargs):
    if not raw and instance.round_id:
        instance.contest = instance.round.contest
    if not raw and not instance.short_name and instance.problem_id:
        short_names = ProblemInstance.objects.filter(contest=instance.contest)\
                .values_list('short_name', flat=True)
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
submission_kinds.register('IGNORED', _("Ignored"))
submission_kinds.register('SUSPECTED', _("Suspected"))

submission_statuses = EnumRegistry()
submission_statuses.register('?', _("Pending"))
submission_statuses.register('OK', _("OK"))
submission_statuses.register('ERR', _("Error"))


class Submission(models.Model):
    problem_instance = models.ForeignKey(ProblemInstance,
            verbose_name=_("problem"))
    user = models.ForeignKey(User, blank=True, null=True,
            verbose_name=_("user"))
    date = models.DateTimeField(default=timezone.now, blank=True,
            verbose_name=_("date"), db_index=True)
    kind = EnumField(submission_kinds, default='NORMAL',
            verbose_name=_("kind"))
    score = ScoreField(blank=True, null=True,
            verbose_name=_("score"))
    status = EnumField(submission_statuses, default='?',
            verbose_name=_("status"))
    comment = models.TextField(blank=True,
            verbose_name=_("comment"))

    @property
    def problem(self):
        return self.problem_instance.problem

    class Meta(object):
        verbose_name = _("submission")
        verbose_name_plural = _("submissions")
        get_latest_by = 'date'

    def is_scored(self):
        return self.score is not None

    def get_date_display(self):
        return self.problem_instance.contest.controller \
                .render_submission_date(self)

    def get_score_display(self):
        if self.score is None:
            return None
        return self.problem_instance.contest.controller \
                .render_submission_score(self)

submission_report_kinds = EnumRegistry()
submission_report_kinds.register('FINAL', _("Final report"))
submission_report_kinds.register('FAILURE', _("Evaluation failure report"))

submission_report_statuses = EnumRegistry()
submission_report_statuses.register('INACTIVE', _("Inactive"))
submission_report_statuses.register('ACTIVE', _("Active"))
submission_report_statuses.register('SUPERSEDED', _("Superseded"))


class SubmissionReport(models.Model):
    submission = models.ForeignKey(Submission)
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
    submission_report = models.ForeignKey(SubmissionReport)
    status = EnumField(submission_statuses, blank=True, null=True)
    score = ScoreField(blank=True, null=True)
    max_score = ScoreField(blank=True, null=True)
    comment = models.TextField(blank=True, null=True)

    def get_score_display(self):
        if self.score is None:
            return ''
        return unicode(self.score)


class FailureReport(models.Model):
    """A report generated when evaluation process failed.

       The submission should have its status set to ``FAILED``. Such reports
       are not shown to users.
    """
    submission_report = models.ForeignKey(SubmissionReport)
    message = models.TextField()
    json_environ = models.TextField()


class UserResultForProblem(models.Model):
    """User result (score) for the problem.

       Each user can have only one class:`UserResultForProblem` per problem
       instance.
    """
    user = models.ForeignKey(User)
    problem_instance = models.ForeignKey(ProblemInstance)
    score = ScoreField(blank=True, null=True)
    status = EnumField(submission_statuses, blank=True, null=True)
    submission_report = models.ForeignKey(SubmissionReport, blank=True,
            null=True)

    class Meta(object):
        unique_together = ('user', 'problem_instance')


class UserResultForRound(models.Model):
    """User result (score) for the round.

       Each user can have only one :class:`UserResultForRound` per round.
    """
    user = models.ForeignKey(User)
    round = models.ForeignKey(Round)
    score = ScoreField(blank=True, null=True)

    class Meta(object):
        unique_together = ('user', 'round')


class UserResultForContest(models.Model):
    """Represents the user result (score) for the contest.

       Each user can have only one :class:`UserResultForContest` per contest
       for given type.
    """
    user = models.ForeignKey(User)
    contest = models.ForeignKey(Contest)
    score = ScoreField(blank=True, null=True)

    class Meta(object):
        unique_together = ('user', 'contest')


class RoundTimeExtension(models.Model):
    """Represents the time the round has been extended by for a certain user.

       The extra time is given in minutes.
    """
    user = models.ForeignKey(User)
    round = models.ForeignKey(Round)
    extra_time = models.PositiveIntegerField(_("Extra time (in minutes)"))

    class Meta(object):
        unique_together = ('user', 'round')
        verbose_name = _("round time extension")
        verbose_name_plural = _("round time extensions")

    def __unicode__(self):
        return unicode(self.round) + ': ' + unicode(self.user)

contest_permissions = EnumRegistry()
contest_permissions.register('contests.contest_admin', _("Admin"))
contest_permissions.register('contests.contest_observer', _("Observer"))
contest_permissions.register('contests.personal_data', _("Personal Data"))


class ContestPermission(models.Model):
    user = models.ForeignKey(User)
    contest = models.ForeignKey(Contest)
    permission = EnumField(contest_permissions,
            default='contests.contest_admin', verbose_name=_("permission"))

    class Meta(object):
        unique_together = ('user', 'contest', 'permission')
        verbose_name = _("contest permission")
        verbose_name_plural = _("contest permissions")

    def __unicode__(self):
        return u'%s/%s: %s' % (self.contest, self.permission, self.user)


class ContestView(models.Model):
    user = models.ForeignKey(User)
    contest = models.ForeignKey(Contest)
    timestamp = models.DateTimeField(default=timezone.now,
                                     verbose_name=_("last view"))

    class Meta(object):
        unique_together = ('user', 'contest')
        index_together = [['user', 'timestamp']]
        get_latest_by = 'timestamp'
        ordering = ('-timestamp', )

    def __unicode__(self):
        return u'%s,%s' % (self.user, self.contest)


class ContestLink(models.Model):
    contest = models.ForeignKey(Contest, verbose_name=_("contest"))
    description = models.CharField(max_length=255,
                                   verbose_name=_("description"))
    url = models.URLField(verbose_name=_("url"))
    order = models.IntegerField(blank=True, null=True)

    class Meta(object):
        verbose_name = _("contest menu link")
        verbose_name_plural = _("contest menu links")


def contest_links_generator(request):
    links = ContestLink.objects.filter(contest=request.contest)
    for link in links:
        # pylint: disable=cell-var-from-loop
        # http://docs.python-guide.org/en/latest/writing/gotchas/#late-binding-closures
        url_generator = lambda request, url=link.url: url
        item = MenuItem(
            name='contest_link_%d' % link.id,
            text=link.description,
            url_generator=url_generator,
            order=link.order
        )
        yield item
menu_registry.register_generator('contest_links', contest_links_generator)
