from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from django.utils.text import get_valid_filename
from django.core.validators import validate_slug
from django.dispatch import receiver
from django.db.models.signals import pre_save, post_save
from django.contrib.auth.models import User
from oioioi.base.fields import DottedNameField, EnumRegistry, EnumField
from oioioi.base.utils import get_object_by_dotted_name
from oioioi.problems.models import Problem
from oioioi.contests.fields import ScoreField
from oioioi.filetracker.fields import FileField

import itertools
import os.path


def make_contest_filename(instance, filename):
    if not isinstance(instance, Problem):
        assert hasattr(instance, 'contest'), 'contest_file_generator used ' \
                'on object %r which does not have \'contest\' attribute' \
                % (instance,)
        instance = getattr(instance, 'contest')
    return 'contests/%s/%s' % (instance.id,
            get_valid_filename(os.path.basename(filename)))

class Contest(models.Model):
    id = models.CharField(max_length=32, primary_key=True,
            validators=[validate_slug], verbose_name=_("ID"))
    name = models.CharField(max_length=255, verbose_name=_("full name"))
    controller_name = DottedNameField(
            'oioioi.contests.controllers.ContestController',
            verbose_name=_("type"))
    creation_date = models.DateTimeField(auto_now_add=True, editable=False,
            verbose_name=_("creation date"))
    default_submissions_limit = models.IntegerField(
            verbose_name=_("default submissions limit"),
            default=settings.DEFAULT_SUBMISSIONS_LIMIT, blank=True)

    class Meta:
        verbose_name = _("contest")
        verbose_name_plural = _("contests")
        get_latest_by = 'creation_date'
        permissions = (
            ('contest_admin', _("Can administer the contest")),
            ('enter_contest', _("Can enter the contest")),
        )

    @property
    def controller(self):
        if not self.controller_name:
            return None
        return get_object_by_dotted_name(self.controller_name)(self)

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
       the contest.

       This may be used for additional materials, like rules, documentation
       etc.
    """
    contest = models.ForeignKey(Contest, related_name='attachments',
            verbose_name=_("contest"))
    description = models.CharField(max_length=255,
            verbose_name=_("description"))
    content = FileField(upload_to=make_contest_filename,
            verbose_name=_("content"))

    class Meta:
        verbose_name = _("attachment")
        verbose_name_plural = _("attachments")

    @property
    def filename(self):
        return os.path.split(self.content.name)[1]

class Round(models.Model):
    contest = models.ForeignKey(Contest, verbose_name=_("contest"))
    name = models.CharField(max_length=255, verbose_name=_("name"))
    start_date = models.DateTimeField(default=timezone.now,
            verbose_name=_("start date"))
    end_date = models.DateTimeField(blank=True, null=True,
            verbose_name=_("end date"))
    results_date = models.DateTimeField(blank=True, null=True,
            verbose_name=_("results date"))

    class Meta:
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

@receiver(pre_save, sender=Round)
def _generate_round_id(sender, instance, raw, **kwargs):
    """Automatically generate a round name if not provided."""
    if not raw and not instance.name:
        num_other_rounds = Round.objects.filter(contest=instance.contest) \
                .exclude(pk=instance.pk).count()
        instance.name = _("Round %d") % (num_other_rounds + 1,)


class ProblemInstance(models.Model):
    contest = models.ForeignKey(Contest, verbose_name=_("contest"))
    round = models.ForeignKey(Round, verbose_name=_("round"))
    problem = models.ForeignKey(Problem, verbose_name=_("problem"))
    short_name = models.CharField(max_length=30, verbose_name=_("short name"))
    submissions_limit = models.IntegerField(blank=True,
        default=settings.DEFAULT_SUBMISSIONS_LIMIT)

    class Meta:
        verbose_name = _("problem instance")
        verbose_name_plural = _("problem instances")
        unique_together = ('contest', 'short_name')
        ordering = ('round', 'short_name')

    def __unicode__(self):
        return '%(name)s (%(short_name)s)' % \
                dict(short_name=self.short_name, name=self.problem.name)

@receiver(pre_save, sender=ProblemInstance)
def _generate_problem_instance_fields(sender, instance, raw, **kwargs):
    if not raw and instance.round_id:
        instance.contest = instance.round.contest
    if not raw and not instance.short_name and instance.problem_id:
        short_names = ProblemInstance.objects.filter(contest=instance.contest)\
                .values_list('short_name', flat=True)
        problem_short_name = instance.problem.short_name
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
            verbose_name=_("date"))
    kind = EnumField(submission_kinds, default='NORMAL',
            verbose_name=_("kind"))
    score = ScoreField(blank=True, null=True,
            verbose_name=_("score"))
    status = EnumField(submission_statuses, default='?',
            verbose_name=_("status"))
    comment = models.TextField(blank=True,
            verbose_name=_("comment"))

    class Meta:
        verbose_name = _("submission")
        verbose_name_plural = _("submissions")
        get_latest_by = 'id'

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

    class Meta:
        get_latest_by = 'creation_date'
        unique_together = ('submission', 'creation_date')

class ScoreReport(models.Model):
    submission_report = models.ForeignKey(SubmissionReport)
    status = EnumField(submission_statuses, blank=True, null=True)
    score = ScoreField(blank=True, null=True)
    comment = models.TextField(blank=True, null=True)

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

    class Meta:
        unique_together = ('user', 'problem_instance')

class UserResultForRound(models.Model):
    """User result (score) for the round.

       Each user can have only one :class:`UserResultForRound` per round.
    """
    user = models.ForeignKey(User)
    round = models.ForeignKey(Round)
    score = ScoreField(blank=True, null=True)

    class Meta:
        unique_together = ('user', 'round')

class UserResultForContest(models.Model):
    """Represents the user result (score) for the contest.

       Each user can have only one :class:`UserResultForContest` per contest
       for given type.
    """
    user = models.ForeignKey(User)
    contest = models.ForeignKey(Contest)
    score = ScoreField(blank=True, null=True)

    class Meta:
        unique_together = ('user', 'contest')

class RoundTimeExtension(models.Model):
    """Represents the time the round has been extended by for a certain user.

       The extra time is given in minutes.
    """
    user = models.ForeignKey(User)
    round = models.ForeignKey(Round)
    extra_time = models.PositiveIntegerField(_("Extra time (in minutes)"))

    class Meta:
        unique_together = ('user', 'round')
        verbose_name = _("round time extension")
        verbose_name_plural = _("round time extensions")

    def __unicode__(self):
        return unicode(self.round) + ': ' + unicode(self.user)
