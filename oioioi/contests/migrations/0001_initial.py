# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import re

import django.core.validators
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models

import oioioi.base.fields
import oioioi.base.utils.validators
import oioioi.contests.fields
import oioioi.contests.models
import oioioi.filetracker.fields


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Contest',
            fields=[
                ('id', models.CharField(max_length=32, serialize=False, verbose_name='ID', primary_key=True, validators=[django.core.validators.RegexValidator(re.compile(b'^[a-z0-9_-]+$'), "Enter a valid 'slug' consisting of lowercase letters, numbers, underscores or hyphens.", b'invalid')])),
                ('name', models.CharField(max_length=255, verbose_name='full name', validators=[oioioi.base.utils.validators.validate_whitespaces])),
                ('controller_name', oioioi.base.fields.DottedNameField(verbose_name='type', superclass='oioioi.contests.controllers.ContestController')),
                ('creation_date', models.DateTimeField(auto_now_add=True, verbose_name='creation date', db_index=True)),
                ('default_submissions_limit', models.IntegerField(default=10, verbose_name='default submissions limit', blank=True)),
                ('contact_email', models.EmailField(help_text='Address of contest owners. Sent emails related to this contest (i.e. submission confirmations) will have the return address set to this value. Defaults to system admins address if left empty.', max_length=75, verbose_name='contact email', blank=True)),
            ],
            options={
                'get_latest_by': 'creation_date',
                'verbose_name': 'contest',
                'verbose_name_plural': 'contests',
                'permissions': (('contest_admin', 'Can administer the contest'), ('contest_observer', 'Can observe the contest'), ('enter_contest', 'Can enter the contest'), ('personal_data', 'Has access to the private data of users')),
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='ContestAttachment',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('description', models.CharField(max_length=255, verbose_name='description')),
                ('content', oioioi.filetracker.fields.FileField(upload_to=oioioi.contests.models.make_contest_filename, verbose_name='content')),
            ],
            options={
                'verbose_name': 'attachment',
                'verbose_name_plural': 'attachments',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='ContestLink',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('description', models.CharField(max_length=255, verbose_name='description')),
                ('url', models.URLField(verbose_name='url')),
                ('order', models.IntegerField(null=True, blank=True)),
            ],
            options={
                'verbose_name': 'contest menu link',
                'verbose_name_plural': 'contest menu links',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='ContestPermission',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('permission', oioioi.base.fields.EnumField(default=b'contests.contest_admin', max_length=64, verbose_name='permission', choices=[(b'contests.contest_admin', 'Admin'), (b'contests.contest_observer', 'Observer'), (b'contests.personal_data', 'Personal Data')])),
            ],
            options={
                'verbose_name': 'contest permission',
                'verbose_name_plural': 'contest permissions',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='ContestView',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('timestamp', models.DateTimeField(default=django.utils.timezone.now, verbose_name='last view')),
            ],
            options={
                'ordering': ('-timestamp',),
                'get_latest_by': 'timestamp',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='FailureReport',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('message', models.TextField()),
                ('json_environ', models.TextField()),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='ProblemInstance',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('short_name', models.CharField(max_length=30, verbose_name='short name', validators=[django.core.validators.RegexValidator(re.compile(b'^[a-z0-9_-]+$'), "Enter a valid 'slug' consisting of lowercase letters, numbers, underscores or hyphens.", b'invalid')])),
                ('submissions_limit', models.IntegerField(default=10, verbose_name='submissions limit', blank=True)),
                ('contest', models.ForeignKey(verbose_name='contest', to='contests.Contest', on_delete=models.CASCADE)),
            ],
            options={
                'ordering': ('round', 'short_name'),
                'verbose_name': 'problem instance',
                'verbose_name_plural': 'problem instances',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='ProblemStatementConfig',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('visible', oioioi.base.fields.EnumField(default=b'AUTO', help_text='If set to Auto, the visibility is determined according to the type of the contest.', max_length=64, verbose_name='statements visibility', choices=[(b'YES', 'Visible'), (b'NO', 'Not visible'), (b'AUTO', 'Auto')])),
                ('contest', models.OneToOneField(to='contests.Contest', on_delete=models.CASCADE)),
            ],
            options={
                'verbose_name': 'problem statement config',
                'verbose_name_plural': 'problem statement configs',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Round',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=255, verbose_name='name', validators=[oioioi.base.utils.validators.validate_whitespaces])),
                ('start_date', models.DateTimeField(default=django.utils.timezone.now, verbose_name='start date')),
                ('end_date', models.DateTimeField(null=True, verbose_name='end date', blank=True)),
                ('results_date', models.DateTimeField(null=True, verbose_name='results date', blank=True)),
                ('public_results_date', models.DateTimeField(help_text="Participants may learn about others' results, what exactly happens depends on the type of the contest (eg. rankings, contestants' solutions are published).", null=True, verbose_name='public results date', blank=True)),
                ('is_trial', models.BooleanField(default=False, verbose_name='is trial')),
                ('contest', models.ForeignKey(verbose_name='contest', to='contests.Contest', on_delete=models.CASCADE)),
            ],
            options={
                'ordering': ('contest', 'start_date'),
                'verbose_name': 'round',
                'verbose_name_plural': 'rounds',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='RoundTimeExtension',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('extra_time', models.PositiveIntegerField(verbose_name='Extra time (in minutes)')),
                ('round', models.ForeignKey(to='contests.Round', on_delete=models.CASCADE)),
                ('user', models.ForeignKey(to=settings.AUTH_USER_MODEL, on_delete=models.CASCADE)),
            ],
            options={
                'verbose_name': 'round time extension',
                'verbose_name_plural': 'round time extensions',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='ScoreReport',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('status', oioioi.base.fields.EnumField(blank=True, max_length=64, null=True, choices=[(b'?', 'Pending'), (b'OK', 'OK'), (b'ERR', 'Error'), (b'CE', 'Compilation failed'), (b'RE', 'Runtime error'), (b'WA', 'Wrong answer'), (b'TLE', 'Time limit exceeded'), (b'MLE', 'Memory limit exceeded'), (b'OLE', 'Output limit exceeded'), (b'SE', 'System error'), (b'RV', 'Rule violation'), (b'INI_OK', 'Initial tests: OK'), (b'INI_ERR', 'Initial tests: failed'), (b'TESTRUN_OK', 'No error'), (b'MSE', 'Outgoing message size limit exceeded'), (b'MCE', 'Outgoing message count limit exceeded'), (b'IGN', 'Ignored')])),
                ('score', oioioi.contests.fields.ScoreField(max_length=255, null=True, blank=True)),
                ('max_score', oioioi.contests.fields.ScoreField(max_length=255, null=True, blank=True)),
                ('comment', models.TextField(null=True, blank=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Submission',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('date', models.DateTimeField(default=django.utils.timezone.now, db_index=True, verbose_name='date', blank=True)),
                ('kind', oioioi.base.fields.EnumField(default=b'NORMAL', max_length=64, verbose_name='kind', choices=[(b'NORMAL', 'Normal'), (b'IGNORED', 'Ignored'), (b'SUSPECTED', 'Suspected'), (b'USER_OUTS', 'Generate user out'), (b'TESTRUN', 'Test run')])),
                ('score', oioioi.contests.fields.ScoreField(max_length=255, null=True, verbose_name='score', blank=True)),
                ('status', oioioi.base.fields.EnumField(default=b'?', max_length=64, verbose_name='status', choices=[(b'?', 'Pending'), (b'OK', 'OK'), (b'ERR', 'Error'), (b'CE', 'Compilation failed'), (b'RE', 'Runtime error'), (b'WA', 'Wrong answer'), (b'TLE', 'Time limit exceeded'), (b'MLE', 'Memory limit exceeded'), (b'OLE', 'Output limit exceeded'), (b'SE', 'System error'), (b'RV', 'Rule violation'), (b'INI_OK', 'Initial tests: OK'), (b'INI_ERR', 'Initial tests: failed'), (b'TESTRUN_OK', 'No error'), (b'MSE', 'Outgoing message size limit exceeded'), (b'MCE', 'Outgoing message count limit exceeded'), (b'IGN', 'Ignored')])),
                ('comment', models.TextField(verbose_name='comment', blank=True)),
                ('problem_instance', models.ForeignKey(verbose_name='problem', to='contests.ProblemInstance', on_delete=models.CASCADE)),
                ('user', models.ForeignKey(verbose_name='user', blank=True, to=settings.AUTH_USER_MODEL, null=True, on_delete=models.CASCADE)),
            ],
            options={
                'get_latest_by': 'date',
                'verbose_name': 'submission',
                'verbose_name_plural': 'submissions',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='SubmissionReport',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('creation_date', models.DateTimeField(auto_now_add=True)),
                ('kind', oioioi.base.fields.EnumField(default=b'FINAL', max_length=64, choices=[(b'FINAL', 'Final report'), (b'FAILURE', 'Evaluation failure report'), (b'INITIAL', 'Initial report'), (b'NORMAL', 'Normal report'), (b'FULL', 'Full report'), (b'HIDDEN', 'Hidden report (for admins only)'), (b'USER_OUTS', 'Report with user out'), (b'TESTRUN', 'Test run report')])),
                ('status', oioioi.base.fields.EnumField(default=b'INACTIVE', max_length=64, choices=[(b'INACTIVE', 'Inactive'), (b'ACTIVE', 'Active'), (b'SUPERSEDED', 'Superseded')])),
                ('submission', models.ForeignKey(to='contests.Submission', on_delete=models.CASCADE)),
            ],
            options={
                'ordering': ('-creation_date',),
                'get_latest_by': 'creation_date',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='UserResultForContest',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('score', oioioi.contests.fields.ScoreField(max_length=255, null=True, blank=True)),
                ('contest', models.ForeignKey(to='contests.Contest', on_delete=models.CASCADE)),
                ('user', models.ForeignKey(to=settings.AUTH_USER_MODEL, on_delete=models.CASCADE)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='UserResultForProblem',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('score', oioioi.contests.fields.ScoreField(max_length=255, null=True, blank=True)),
                ('status', oioioi.base.fields.EnumField(blank=True, max_length=64, null=True, choices=[(b'?', 'Pending'), (b'OK', 'OK'), (b'ERR', 'Error'), (b'CE', 'Compilation failed'), (b'RE', 'Runtime error'), (b'WA', 'Wrong answer'), (b'TLE', 'Time limit exceeded'), (b'MLE', 'Memory limit exceeded'), (b'OLE', 'Output limit exceeded'), (b'SE', 'System error'), (b'RV', 'Rule violation'), (b'INI_OK', 'Initial tests: OK'), (b'INI_ERR', 'Initial tests: failed'), (b'TESTRUN_OK', 'No error'), (b'MSE', 'Outgoing message size limit exceeded'), (b'MCE', 'Outgoing message count limit exceeded'), (b'IGN', 'Ignored')])),
                ('problem_instance', models.ForeignKey(to='contests.ProblemInstance', on_delete=models.CASCADE)),
                ('submission_report', models.ForeignKey(blank=True, to='contests.SubmissionReport', null=True, on_delete=models.CASCADE)),
                ('user', models.ForeignKey(to=settings.AUTH_USER_MODEL, on_delete=models.CASCADE)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='UserResultForRound',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('score', oioioi.contests.fields.ScoreField(max_length=255, null=True, blank=True)),
                ('round', models.ForeignKey(to='contests.Round', on_delete=models.CASCADE)),
                ('user', models.ForeignKey(to=settings.AUTH_USER_MODEL, on_delete=models.CASCADE)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.AlterUniqueTogether(
            name='userresultforround',
            unique_together=set([('user', 'round')]),
        ),
        migrations.AlterUniqueTogether(
            name='userresultforproblem',
            unique_together=set([('user', 'problem_instance')]),
        ),
        migrations.AlterUniqueTogether(
            name='userresultforcontest',
            unique_together=set([('user', 'contest')]),
        ),
        migrations.AddField(
            model_name='scorereport',
            name='submission_report',
            field=models.ForeignKey(to='contests.SubmissionReport', on_delete=models.CASCADE),
            preserve_default=True,
        ),
        migrations.AlterUniqueTogether(
            name='roundtimeextension',
            unique_together=set([('user', 'round')]),
        ),
        migrations.AlterUniqueTogether(
            name='round',
            unique_together=set([('contest', 'name')]),
        ),
    ]
