import os
import json

from django.db import models
from django.utils.translation import ugettext_lazy as _

from oioioi.base.utils.deps import check_django_app_dependencies
from oioioi.contests.models import submission_statuses
from oioioi.problems.models import Problem
from oioioi.programs.models import TestReport


check_django_app_dependencies(__name__, ['oioioi.testrun'], strict=True)
check_django_app_dependencies(__name__, ['oioioi.submitsqueue'])


submission_statuses.register('MSE', _("Outgoing message size limit exceeded"))
submission_statuses.register('MCE', _("Outgoing message count limit exceeded"))


class ZeusProblemData(models.Model):
    problem = models.OneToOneField(Problem, primary_key=True)
    zeus_id = models.CharField(max_length=255)
    zeus_problem_id = models.IntegerField(default=0)


class ZeusAsyncJob(models.Model):
    check_uid = models.CharField(primary_key=True, max_length=255)
    environ = models.TextField()
    resumed = models.BooleanField(default=False)

    @property
    def env(self):
        return json.loads(self.environ)

    @property
    def submission_id(self):
        return self.env.get('submission_id', None)

    @property
    def zeus_problem_id(self):
        return self.env.get('zeus_problem_id', None)

    def __repr__(self):
        res = 'Resumed' if self.resumed else ''
        return '%sJob(%s, subm=%s, problem=%s)' % (res, self.check_uid,
                self.submission_id, self.zeus_problem_id)

def make_custom_library_filename(instance, filename):
    if not instance.id:
        instance.save()
    return 'testruns/%s/%d/lib%s' % (instance.problem_instance.contest.id,
            instance.id, os.path.splitext(filename)[1])

class ZeusTestReport(TestReport):
    nodes = models.IntegerField(null=True)
    check_uid = models.CharField(max_length=255)
