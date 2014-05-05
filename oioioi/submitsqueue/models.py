from django.db import models
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _

from oioioi.contests.models import Submission
from oioioi.base.fields import EnumRegistry, EnumField


submission_states = EnumRegistry()
submission_states.register('QUEUED', _("Queued"))
submission_states.register('PROGRESS', _("In progress"))
submission_states.register('PROGRESS-RESUMED', _("In progress (resumed)"))
submission_states.register('CANCELLED', _("Cancelled"))
submission_states.register('WAITING', _("Waiting"))


class QueuedSubmit(models.Model):
    submission = models.ForeignKey(Submission)
    state = EnumField(submission_states, default='QUEUED')
    creation_date = models.DateTimeField(default=timezone.now)
    celery_task_id = models.CharField(max_length=50, unique=True, null=True,
                                      blank=True)

    creation_date.short_description = _("Creation date")

    class Meta(object):
        verbose_name = _("Queued Submit")
        ordering = ['pk']
