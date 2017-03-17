import json

from django.db import models
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _

from oioioi.contests.models import Submission
from oioioi.base.fields import EnumRegistry, EnumField


job_states = EnumRegistry()
job_states.register('QUEUED', _("Queued"))
job_states.register('PROGRESS', _("In progress"))
job_states.register('CANCELLED', _("Cancelled"))
job_states.register('WAITING', _("Waiting"))


class QueuedJob(models.Model):
    job_id = models.CharField(max_length=50, primary_key=True)
    state = EnumField(job_states, default='QUEUED')
    creation_date = models.DateTimeField(default=timezone.now)

    # Optional information about queued jobs.
    submission = models.ForeignKey(Submission, null=True)
    celery_task_id = models.CharField(max_length=50, unique=True, null=True,
                                      blank=True)

    class Meta(object):
        verbose_name = _("Queued job")
        verbose_name_plural = _("Queued jobs")
        ordering = ['pk']


class SavedEnviron(models.Model):
    # A queued_job field can't be a primary key for this model, as it would
    # cause evalmgr to 'resume' job with results from previous asynchronous
    # call.
    queued_job = models.OneToOneField(QueuedJob, on_delete=models.CASCADE)
    environ = models.TextField(help_text=_("JSON-encoded evaluation environ"))
    save_time = models.DateTimeField(auto_now=True,
            help_text=_("Time and date when the environ was saved"))

    def load_environ(self):
        return json.loads(self.environ)

    @classmethod
    def save_environ(cls, environ):
        return cls.objects.create(
                queued_job=QueuedJob.objects.get(job_id=environ['job_id']),
                environ=json.dumps(environ))
