# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


def assign_tests_to_problem_instances(apps, schema_editor):
    """For each test, assigns it to main_problem_instance
       of the :class:`oioioi.problems.model.Problem`.
    """
    Test = apps.get_model('programs', 'Test')
    for test in Test.objects.all():
        test.problem_instance = test.problem.main_problem_instance
        test.save()


class Migration(migrations.Migration):

    dependencies = [
        ('contests', '0004_auto_20150420_2002'),
        ('programs', '0002_auto_20150218_1346'),
        ('problems', '0004_problem_main_problem_instance'),
    ]

    operations = [
        migrations.AddField(
            model_name='test',
            name='problem_instance',
            field=models.ForeignKey(default=None, to='contests.ProblemInstance', null=True, on_delete=models.CASCADE),
            preserve_default=False,
        ),
        migrations.AlterUniqueTogether(
            name='test',
            unique_together=set([('problem_instance', 'name')]),
        ),
        migrations.RunPython(assign_tests_to_problem_instances),
        migrations.AlterField(
            model_name='test',
            name='problem_instance',
            field=models.ForeignKey(to='contests.ProblemInstance', null=False, blank=False, on_delete=models.CASCADE),
            preserve_default=False
        ),
        migrations.RemoveField(
            model_name='test',
            name='problem',
        ),
    ]
