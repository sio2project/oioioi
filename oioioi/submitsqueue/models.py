from django.db import models
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from oioioi.contests.models import Submission
from oioioi.base.fields import EnumRegistry, EnumField


submission_states = EnumRegistry()
submission_states.register('QUEUED', _("Queued"))
submission_states.register('PROGRESS', _("In progress"))


class QueuedSubmit(models.Model):
    submission = models.ForeignKey(Submission, primary_key=True)
    state = EnumField(submission_states, default='QUEUED')
    creation_date = models.DateTimeField(default=timezone.now)
    celery_task_id = models.CharField(max_length=50, unique=True, null=True,
                                      blank=True)

    class Meta(object):
        verbose_name = _("Queued Submit")

    @property
    def problem_instance(self):
        return self.submission.problem_instance

    @property
    def contest(self):
        return self.submission.problem_instance.contest

    @property
    def user(self):
        return self.submission.user
