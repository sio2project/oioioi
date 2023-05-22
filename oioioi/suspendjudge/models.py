from django.db import models
from django.utils.translation import gettext_lazy as _

from oioioi.contests.models import ProblemInstance
from oioioi.evalmgr.models import job_states

job_states.register('SUSPENDED', _("Suspended"))


class SuspendedProblem(models.Model):
    problem_instance = models.OneToOneField(
        ProblemInstance, related_name='suspended', on_delete=models.CASCADE
    )
    suspend_init_tests = models.BooleanField(default=True)
