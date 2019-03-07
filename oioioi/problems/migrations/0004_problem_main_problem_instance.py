# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


def assign_problem_instances(apps, schema_editor):
    """Finds :class:`oioioi.contests.models.ProblemInstance` assigned to every
       :class:`oioioi.problems.models.Problem`,
       and makes it a main_problem_instance.

       This function assumes that each :class:`oioioi.problems.models.Problem`
       has exactly one corresponding
       :class:`oioioi.contests.models.ProblemInstance`.
    """
    Problem = apps.get_model('problems', 'Problem')
    for problem in Problem.objects.all():
        pi = problem.probleminstance_set.get()
        problem.main_problem_instance = pi
        problem.save()


class Migration(migrations.Migration):

    dependencies = [
        ('contests', '0004_auto_20150420_2002'),
        ('problems', '0003_problemsite'),
    ]

    operations = [
        migrations.AddField(
            model_name='problem',
            name='main_problem_instance',
            field=models.ForeignKey(related_name='main_problem_instance', verbose_name='main problem instance', blank=False, to='contests.ProblemInstance', null=True, on_delete=models.CASCADE),
            preserve_default=True,
        ),
        migrations.RunPython(assign_problem_instances),
    ]
