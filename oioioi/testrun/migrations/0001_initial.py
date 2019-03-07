# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models

import oioioi.base.fields
import oioioi.filetracker.fields
import oioioi.testrun.models


class Migration(migrations.Migration):

    dependencies = [
        ('contests', '0001_initial'),
        ('problems', '0001_initial'),
        ('programs', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='TestRunConfig',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('time_limit', models.IntegerField(null=True, verbose_name='time limit (ms)', blank=True)),
                ('memory_limit', models.IntegerField(null=True, verbose_name='memory limit (KiB)', blank=True)),
                ('problem', models.OneToOneField(related_name='test_run_config', verbose_name='problem', to='problems.Problem')),
            ],
            options={
                'verbose_name': 'test run config',
                'verbose_name_plural': 'test run configs',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='TestRunProgramSubmission',
            fields=[
                ('programsubmission_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='programs.ProgramSubmission')),
                ('input_file', oioioi.filetracker.fields.FileField(upload_to=oioioi.testrun.models.make_custom_input_filename)),
            ],
            options={
            },
            bases=('programs.programsubmission',),
        ),
        migrations.CreateModel(
            name='TestRunReport',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('status', oioioi.base.fields.EnumField(max_length=64, choices=[(b'?', 'Pending'), (b'OK', 'OK'), (b'ERR', 'Error'), (b'CE', 'Compilation failed'), (b'RE', 'Runtime error'), (b'WA', 'Wrong answer'), (b'TLE', 'Time limit exceeded'), (b'MLE', 'Memory limit exceeded'), (b'OLE', 'Output limit exceeded'), (b'SE', 'System error'), (b'RV', 'Rule violation'), (b'INI_OK', 'Initial tests: OK'), (b'INI_ERR', 'Initial tests: failed'), (b'TESTRUN_OK', 'No error'), (b'MSE', 'Outgoing message size limit exceeded'), (b'MCE', 'Outgoing message count limit exceeded'), (b'IGN', 'Ignored')])),
                ('comment', models.CharField(max_length=255, blank=True)),
                ('time_used', models.IntegerField(blank=True)),
                ('test_time_limit', models.IntegerField(null=True, blank=True)),
                ('output_file', oioioi.filetracker.fields.FileField(upload_to=oioioi.testrun.models.make_custom_output_filename)),
                ('submission_report', models.ForeignKey(to='contests.SubmissionReport', on_delete=models.CASCADE)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
    ]
