# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('contests', '0007_auto_20161214_1411'),
        ('submitsqueue', '0002_auto_20161214_1411'),
        ('zeus', '0002_auto_20150414_1950'),
    ]

    operations = [
        migrations.DeleteModel(
            name='ZeusFetchSeq',
        ),
        migrations.RemoveField(
            model_name='zeustestrunprogramsubmission',
            name='testrunprogramsubmission_ptr',
        ),
        migrations.RemoveField(
            model_name='zeustestrunreport',
            name='testrunreport_ptr',
        ),
        migrations.DeleteModel(
            name='ZeusTestRunProgramSubmission',
        ),
        migrations.DeleteModel(
            name='ZeusTestRunReport',
        ),
    ]
