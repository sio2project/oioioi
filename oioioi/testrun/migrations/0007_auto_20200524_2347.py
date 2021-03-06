# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2020-05-24 21:47
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('testrun', '0006_migrate_configs'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='testrunconfig',
            name='problem',
        ),
        migrations.AlterField(
            model_name='testrunconfigforinstance',
            name='memory_limit',
            field=models.IntegerField(default=131072, verbose_name='memory limit (KiB)'),
        ),
        migrations.AlterField(
            model_name='testrunconfigforinstance',
            name='time_limit',
            field=models.IntegerField(default=10000, verbose_name='time limit (ms)'),
        ),
        migrations.DeleteModel(
            name='TestRunConfig',
        ),
        migrations.RenameModel(
            old_name='TestRunConfigForInstance',
            new_name='TestRunConfig'
        ),
    ]
