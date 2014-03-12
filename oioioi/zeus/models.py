from django.db import models

from oioioi.problems.models import Problem


class ZeusProblemData(models.Model):
    problem = models.OneToOneField(Problem, primary_key=True)
    zeus_id = models.CharField(max_length=255)
    zeus_problem_id = models.IntegerField(default=0)
