# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import django.db.models.deletion
from django.db import migrations, models

import oioioi.base.fields
import oioioi.contests.fields
import oioioi.filetracker.fields
import oioioi.problems.models
import oioioi.programs.models


class Migration(migrations.Migration):

    dependencies = [
        ('contests', '0001_initial'),
        ('problems', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='CompilationReport',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('status', oioioi.base.fields.EnumField(max_length=64, choices=[(b'?', 'Pending'), (b'OK', 'OK'), (b'ERR', 'Error'), (b'CE', 'Compilation failed'), (b'RE', 'Runtime error'), (b'WA', 'Wrong answer'), (b'TLE', 'Time limit exceeded'), (b'MLE', 'Memory limit exceeded'), (b'OLE', 'Output limit exceeded'), (b'SE', 'System error'), (b'RV', 'Rule violation'), (b'INI_OK', 'Initial tests: OK'), (b'INI_ERR', 'Initial tests: failed'), (b'TESTRUN_OK', 'No error'), (b'MSE', 'Outgoing message size limit exceeded'), (b'MCE', 'Outgoing message count limit exceeded'), (b'IGN', 'Ignored')])),
                ('compiler_output', models.TextField()),
                ('submission_report', models.ForeignKey(to='contests.SubmissionReport')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='GroupReport',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('group', models.CharField(max_length=30)),
                ('score', oioioi.contests.fields.ScoreField(max_length=255, null=True, blank=True)),
                ('max_score', oioioi.contests.fields.ScoreField(max_length=255, null=True, blank=True)),
                ('status', oioioi.base.fields.EnumField(max_length=64, choices=[(b'?', 'Pending'), (b'OK', 'OK'), (b'ERR', 'Error'), (b'CE', 'Compilation failed'), (b'RE', 'Runtime error'), (b'WA', 'Wrong answer'), (b'TLE', 'Time limit exceeded'), (b'MLE', 'Memory limit exceeded'), (b'OLE', 'Output limit exceeded'), (b'SE', 'System error'), (b'RV', 'Rule violation'), (b'INI_OK', 'Initial tests: OK'), (b'INI_ERR', 'Initial tests: failed'), (b'TESTRUN_OK', 'No error'), (b'MSE', 'Outgoing message size limit exceeded'), (b'MCE', 'Outgoing message count limit exceeded'), (b'IGN', 'Ignored')])),
                ('submission_report', models.ForeignKey(to='contests.SubmissionReport')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='LibraryProblemData',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('libname', models.CharField(help_text='Filename library should be given during compilation', max_length=30, verbose_name='libname')),
            ],
            options={
                'verbose_name': 'library problem data',
                'verbose_name_plural': 'library problem data',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='ModelSolution',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=30, verbose_name='name')),
                ('source_file', oioioi.filetracker.fields.FileField(upload_to=oioioi.problems.models.make_problem_filename, verbose_name='source')),
                ('kind', oioioi.base.fields.EnumField(max_length=64, verbose_name='kind', choices=[(b'NORMAL', 'Model solution'), (b'SLOW', 'Slow solution'), (b'INCORRECT', 'Incorrect solution')])),
                ('order_key', models.IntegerField(default=0)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='OutputChecker',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('exe_file', oioioi.filetracker.fields.FileField(upload_to=oioioi.problems.models.make_problem_filename, null=True, verbose_name='checker executable file', blank=True)),
            ],
            options={
                'verbose_name': 'output checker',
                'verbose_name_plural': 'output checkers',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='ProgramSubmission',
            fields=[
                ('submission_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='contests.Submission')),
                ('source_file', oioioi.filetracker.fields.FileField(upload_to=oioioi.programs.models.make_submission_filename)),
                ('source_length', models.IntegerField(null=True, verbose_name='Source code length', blank=True)),
            ],
            options={
            },
            bases=('contests.submission',),
        ),
        migrations.CreateModel(
            name='ModelProgramSubmission',
            fields=[
                ('programsubmission_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='programs.ProgramSubmission')),
            ],
            options={
            },
            bases=('programs.programsubmission',),
        ),
        migrations.CreateModel(
            name='ReportActionsConfig',
            fields=[
                ('problem', models.OneToOneField(related_name='report_actions_config', primary_key=True, serialize=False, to='problems.Problem', verbose_name='problem instance')),
                ('can_user_generate_outs', models.BooleanField(default=False, verbose_name='Allow users to generate their outs on tests from visible reports.')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Test',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=30, verbose_name='name')),
                ('input_file', oioioi.filetracker.fields.FileField(upload_to=oioioi.problems.models.make_problem_filename, null=True, verbose_name='input', blank=True)),
                ('output_file', oioioi.filetracker.fields.FileField(upload_to=oioioi.problems.models.make_problem_filename, null=True, verbose_name='output/hint', blank=True)),
                ('kind', oioioi.base.fields.EnumField(max_length=64, verbose_name='kind', choices=[(b'NORMAL', 'Normal test'), (b'EXAMPLE', 'Example test')])),
                ('group', models.CharField(max_length=30, verbose_name='group')),
                ('time_limit', models.IntegerField(null=True, verbose_name='time limit (ms)', validators=[oioioi.programs.models.validate_time_limit])),
                ('memory_limit', models.IntegerField(null=True, verbose_name='memory limit (KiB)', blank=True)),
                ('max_score', models.IntegerField(default=10, verbose_name='score')),
                ('order', models.IntegerField(default=0)),
                ('problem', models.ForeignKey(to='problems.Problem')),
            ],
            options={
                'ordering': ['order'],
                'verbose_name': 'test',
                'verbose_name_plural': 'tests',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='TestReport',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('status', oioioi.base.fields.EnumField(max_length=64, choices=[(b'?', 'Pending'), (b'OK', 'OK'), (b'ERR', 'Error'), (b'CE', 'Compilation failed'), (b'RE', 'Runtime error'), (b'WA', 'Wrong answer'), (b'TLE', 'Time limit exceeded'), (b'MLE', 'Memory limit exceeded'), (b'OLE', 'Output limit exceeded'), (b'SE', 'System error'), (b'RV', 'Rule violation'), (b'INI_OK', 'Initial tests: OK'), (b'INI_ERR', 'Initial tests: failed'), (b'TESTRUN_OK', 'No error'), (b'MSE', 'Outgoing message size limit exceeded'), (b'MCE', 'Outgoing message count limit exceeded'), (b'IGN', 'Ignored')])),
                ('comment', models.CharField(max_length=255, blank=True)),
                ('score', oioioi.contests.fields.ScoreField(max_length=255, null=True, blank=True)),
                ('time_used', models.IntegerField(blank=True)),
                ('output_file', oioioi.filetracker.fields.FileField(null=True, upload_to=oioioi.programs.models.make_output_filename, blank=True)),
                ('test_name', models.CharField(max_length=30)),
                ('test_group', models.CharField(max_length=30)),
                ('test_time_limit', models.IntegerField(null=True, blank=True)),
                ('test_max_score', models.IntegerField(null=True, blank=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='UserOutGenStatus',
            fields=[
                ('testreport', models.OneToOneField(related_name='userout_status', primary_key=True, serialize=False, to='programs.TestReport')),
                ('status', oioioi.base.fields.EnumField(default=b'?', max_length=64, choices=[(b'?', 'Pending'), (b'OK', 'OK'), (b'ERR', 'Error'), (b'CE', 'Compilation failed'), (b'RE', 'Runtime error'), (b'WA', 'Wrong answer'), (b'TLE', 'Time limit exceeded'), (b'MLE', 'Memory limit exceeded'), (b'OLE', 'Output limit exceeded'), (b'SE', 'System error'), (b'RV', 'Rule violation'), (b'INI_OK', 'Initial tests: OK'), (b'INI_ERR', 'Initial tests: failed'), (b'TESTRUN_OK', 'No error'), (b'MSE', 'Outgoing message size limit exceeded'), (b'MCE', 'Outgoing message count limit exceeded'), (b'IGN', 'Ignored')])),
                ('visible_for_user', models.BooleanField(default=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.AddField(
            model_name='testreport',
            name='submission_report',
            field=models.ForeignKey(to='contests.SubmissionReport'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='testreport',
            name='test',
            field=models.ForeignKey(on_delete=django.db.models.deletion.SET_NULL, blank=True, to='programs.Test', null=True),
            preserve_default=True,
        ),
        migrations.AlterUniqueTogether(
            name='test',
            unique_together=set([('problem', 'name')]),
        ),
        migrations.AddField(
            model_name='outputchecker',
            name='problem',
            field=models.OneToOneField(to='problems.Problem'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='modelsolution',
            name='problem',
            field=models.ForeignKey(to='problems.Problem'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='modelprogramsubmission',
            name='model_solution',
            field=models.ForeignKey(to='programs.ModelSolution'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='libraryproblemdata',
            name='problem',
            field=models.OneToOneField(to='problems.Problem'),
            preserve_default=True,
        ),
    ]
