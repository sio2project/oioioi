# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models

import oioioi.filetracker.fields
import oioioi.zeus.models


class Migration(migrations.Migration):

    dependencies = [
        ('problems', '0001_initial'),
        ('testrun', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='ZeusAsyncJob',
            fields=[
                ('check_uid', models.IntegerField(serialize=False, primary_key=True)),
                ('environ', models.TextField()),
                ('resumed', models.BooleanField(default=False)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='ZeusFetchSeq',
            fields=[
                ('zeus_id', models.CharField(max_length=255, serialize=False, primary_key=True)),
                ('next_seq', models.IntegerField(default=0)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='ZeusProblemData',
            fields=[
                ('problem', models.OneToOneField(primary_key=True, serialize=False, to='problems.Problem', on_delete=models.CASCADE)),
                ('zeus_id', models.CharField(max_length=255)),
                ('zeus_problem_id', models.IntegerField(default=0)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='ZeusTestRunProgramSubmission',
            fields=[
                ('testrunprogramsubmission_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='testrun.TestRunProgramSubmission', on_delete=models.CASCADE)),
                ('library_file', oioioi.filetracker.fields.FileField(null=True, upload_to=oioioi.zeus.models.make_custom_library_filename)),
            ],
            options={
            },
            bases=('testrun.testrunprogramsubmission',),
        ),
        migrations.CreateModel(
            name='ZeusTestRunReport',
            fields=[
                ('testrunreport_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='testrun.TestRunReport', on_delete=models.CASCADE)),
                ('full_out_size', models.IntegerField()),
                ('full_out_handle', models.CharField(max_length=255, blank=True)),
            ],
            options={
            },
            bases=('testrun.testrunreport',),
        ),
    ]
