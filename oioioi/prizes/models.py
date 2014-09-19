import logging
import os.path
from datetime import timedelta
from django.db import models, transaction
from django.contrib.auth.models import User
from django.utils.translation import ugettext_lazy as _
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.conf import settings
from django.template.loader import render_to_string
from django.forms.models import model_to_dict
from django.core.validators import MinValueValidator
from django.utils.text import get_valid_filename
from django.core.files.base import ContentFile
from celery.task import task
from oioioi.contests.models import Contest
from oioioi.base.fields import EnumField, EnumRegistry
from oioioi.filetracker.fields import FileField
from oioioi.prizes.reports import generate_success_report


logger = logging.getLogger(__name__)


class AssignmentNotFound(Exception):
    def __init__(self, prize_giving, email_msg=None, report=None):
        super(AssignmentNotFound, self).__init__()
        self.prize_giving = prize_giving
        self.email_msg = email_msg
        self.report = report

    def send_email(self):
        m = self.email_msg
        if m is not None:
            name, _distributor = self.prize_giving.contest.controller \
                    .get_prizes_distributors()[self.prize_giving.key]
            context = {
                    'prize_giving': self.prize_giving,
                    'key_name': name,
            }
            m.subject = render_to_string(
                    'prizes/email_subject.txt', context).strip()
            m.body += render_to_string('prizes/email_footer.txt', context)
            m.from_email = settings.SERVER_EMAIL
            m.to = self.prize_giving.contest.controller \
                    .get_prizes_email_addresses(self.prize_giving)
            m.send()


@task(ignore_result=True)
@transaction.commit_on_success
def prizesmgr_job(pg_pk, version):
    prefix = "PrizeGiving finalization(id: %s, version: %s): " \
            % (pg_pk, version)
    logger.info(prefix + "beginning...")

    try:
        pg = PrizeGiving.objects.select_for_update().get(pk=pg_pk)
    except PrizeGiving.DoesNotExist:
        return logger.info(prefix + "PG object with given id doesn't exist")

    if pg.version != version:
        return logger.info(prefix + "version doesn't match -- %s / %s",
                           version, pg.version)

    on_success = lambda: logger.info(prefix + "success")
    on_failure = lambda: logger.info(prefix + "prizes assignment not found")

    pg._distribute(on_success, on_failure)


prizegiving_states = EnumRegistry()
prizegiving_states.register('NOT_SCHEDULED', _("NOT SCHEDULED"))
prizegiving_states.register('SCHEDULED', _("SCHEDULED"))
prizegiving_states.register('FAILURE', _("FAILURE"))
prizegiving_states.register('SUCCESS', _("SUCCESS"))


def _make_report_filename(instance, filename):
    return 'prizes/reports/%s/%s/' % (instance.contest.id,
            get_valid_filename(os.path.basename(filename)))


class PrizeGiving(models.Model):
    """Represents an event of distributing prizes to users.

       Such an event needs some proper preparation.
       First of all, we decide on a date when it's going to happen.
       Secondly, we decide on a list of Prizes to be distributed.
       Finally, we specify a distributor, which will effectively assign Prizes
       to users creating PrizeForUser objects.

       To make it all work together, we set up a celery worker to which we send
       scheduled distribution tasks. Each time a PrizeGiving object is
       changed in a way that makes recently sent task irrelevant the task
       is invalidated and a new task is sent if needed.
    """
    # Usage:
    # pg = PrizeGiving.objects.create(contest=c, date=..., name=..., key=...)
    # Prize.objects.create(contest=c, prize_giving=pg, ...)
    # pg.schedule() -- you don't have to call it immediately
    #
    # You can change parameters if ``pg`` hasn't taken place yet:
    # pg.update(contest=..., date=..., name=..., key=...)
    # pg.schedule()
    #
    # Later, when ``pg`` has already succeeded or failed,
    # in order to undo everything and start the logic again,
    # you will need to specify 'force_reset=True' with ``update``:
    # pg.update(force_reset=True, ...)
    # pg.schedule()
    #
    # At any time you can delete ``pg`` as if it has never existed.
    # pg.delete()

    contest = models.ForeignKey(Contest)
    date = models.DateTimeField(
            _("Distribution date"), blank=True, null=True,
            help_text=_("Leave blank for 'later'."))
    name = models.CharField(
            _("name"), max_length=100,
            help_text=_("Prize-givings with the same name "
                        "are listed together."))
    # key in dictionary returned by ContestController.get_prizes_distributors()
    key = models.CharField(_("awarding rules"),
                           max_length=100, choices=[('', '')])

    # read-only fields
    state = EnumField(prizegiving_states, default='NOT_SCHEDULED',
                      editable=False)
    report = FileField(upload_to=_make_report_filename, null=True,
                       editable=False)

    # private fields
    version = models.DateTimeField(default=timezone.now, editable=False)

    class Meta(object):
        verbose_name = _("prize-giving")
        verbose_name_plural = _("prize-givings")
        ordering = ['-date', 'id']

    def _distribute(self, on_success=lambda: None, on_failure=lambda: None):
        try:
            _name, distributor = \
                    self.contest.controller.get_prizes_distributors()[self.key]
            distributor(self)
            self.state = 'SUCCESS'
            report = generate_success_report(self)
            on_success()
        except AssignmentNotFound as e:
            e.send_email()
            self.date = None
            self.state = 'FAILURE'
            report = e.report
            on_failure()
            # The related PrizeForUsers are deleted in call to `save`.

        self._set_report(report)
        self._change_version()
        self.save()

    def _set_report(self, report):
        if report is not None:
            filename = 'id%s__v%s__%s.csv' % \
                    (self.id, self.version, self.state)
            report = ContentFile(report, filename)

        self.report = report

    def _send_task_to_worker(self):
        prizesmgr_job.apply_async(args=[self.pk, self.version], eta=self.date)

    def _delegate_distribution(self):
        self.state = 'SCHEDULED'
        self.save()
        self._send_task_to_worker()

    def _distribute_in_place(self):
        self.date = timezone.now()
        self._distribute()

    def schedule(self):
        """Schedule to happen.

           You need to call it both after creating a new PrizeGiving
           or updating an old one.
           Note, that here we refer to an event rather than a particular
           PrizeGiving instance representing it. For example, you can save
           information about PrizeGiving to the database using a PrizeGiving
           instance, retrieve a new instance representing it two days later,
           and call `schedule` on it.

           If PrizeGiving is past its date, the distribution will be
           triggered from within this funtion.

           It calls `save` behind the scenes.
        """
        if self.state == 'NOT_SCHEDULED' and self.date:
            self._change_version()
            # Take into account that user chooses "now" with 1 minute accuracy
            if self.date >= timezone.now() + timedelta(minutes=1):
                self._delegate_distribution()
            else:
                self._distribute_in_place()

    def _celery_task_invalid(self):
        """Check if there is a valid celery task that now must be invalidated.
        """
        try:
            old_self = PrizeGiving.objects.select_for_update().get(pk=self.pk)
        except PrizeGiving.DoesNotExist:
            old_self = PrizeGiving()

        if old_self.state != 'SCHEDULED':
            return False

        def essential_params(pg):
            return model_to_dict(pg, fields=['state', 'date'])

        return essential_params(old_self) != essential_params(self)

    def _change_version(self):
        self.version = timezone.now()

    def update(self, commit=True, force_reset=False, **kwargs):
        """Always call this method after changing public attributes.
           For convenience, you can set attributes and update in one step
           using keyword arguments.
        """
        for key, value in kwargs.items():
            setattr(self, key, value)

        if force_reset:
            self._set_report(None)

        if force_reset or self._celery_task_invalid():
            self.state = 'NOT_SCHEDULED'
            self._change_version()

        # In case the previous state was 'SUCCESS' and it changed, the
        # related PrizeForUsers are deleted in call to `save`.

        if commit:
            self.save()

    def save(self, *args, **kwargs):
        # PrizeGiving can have related PrizeForUsers in 'SUCCESS' state only.
        if self.state != 'SUCCESS':
            PrizeForUser.objects.filter(prize__prize_giving=self).delete()

        return super(PrizeGiving, self).save(*args, **kwargs)

    def clean_fields(self, *args, **kwargs):
        if 'key' not in kwargs['exclude']:
            kwargs['exclude'].append('key')
        super(PrizeGiving, self).clean_fields(*args, **kwargs)

    def clean(self):
        if self.key not in self.contest.controller.get_prizes_distributors():
            raise ValidationError(
                    _("Invalid value for position in distribution order."))

    def __unicode__(self):
        suffix = timezone.localtime(self.date).strftime(' (%m-%d %H:%M)') \
                if self.date else ''
        return self.name + suffix


class Prize(models.Model):
    contest = models.ForeignKey(Contest)
    prize_giving = models.ForeignKey(PrizeGiving,
                                     verbose_name=_("prize-giving"))
    name = models.CharField(_("name"), max_length=100)
    quantity = models.IntegerField(_("quantity"), default=1,
                                   validators=[MinValueValidator(1)])
    order = models.IntegerField(_("position in non-strict distribution order"),
                                validators=[MinValueValidator(1)])

    class Meta(object):
        verbose_name = _("prize")
        verbose_name_plural = _("prizes")
        ordering = ['prize_giving', 'order', 'id']

    def __unicode__(self):
        return self.name


class PrizeForUser(models.Model):
    user = models.ForeignKey(User)
    prize = models.ForeignKey(Prize)

    class Meta(object):
        ordering = ['prize', 'user']

    def __unicode__(self):
        return unicode(self.user) + ' -> ' + unicode(self.prize)
