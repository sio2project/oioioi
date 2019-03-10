# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import re

import django.core.validators
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models

import oioioi.base.fields
import oioioi.filetracker.fields
import oioioi.problems.models


class Migration(migrations.Migration):

    dependencies = [
        ('contests', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Problem',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=255, verbose_name='full name')),
                ('short_name', models.CharField(max_length=30, verbose_name='short name', validators=[django.core.validators.RegexValidator(re.compile('^[-a-zA-Z0-9_]+$'), "Enter a valid 'slug' consisting of letters, numbers, underscores or hyphens.", 'invalid')])),
                ('controller_name', oioioi.base.fields.DottedNameField(verbose_name='type', superclass='oioioi.problems.controllers.ProblemController')),
                ('package_backend_name', oioioi.base.fields.DottedNameField(null=True, verbose_name='package type', superclass='oioioi.problems.package.ProblemPackageBackend', blank=True)),
                ('contest', models.ForeignKey(verbose_name='contest', blank=True, to='contests.Contest', null=True)),
            ],
            options={
                'verbose_name': 'problem',
                'verbose_name_plural': 'problems',
                'permissions': (('problems_db_admin', 'Can administer the problems database'), ('problem_admin', 'Can administer the problem')),
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='ProblemAttachment',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('description', models.CharField(max_length=255, verbose_name='description')),
                ('content', oioioi.filetracker.fields.FileField(upload_to=oioioi.problems.models.make_problem_filename, verbose_name='content')),
                ('problem', models.ForeignKey(related_name='attachments', to='problems.Problem')),
            ],
            options={
                'verbose_name': 'attachment',
                'verbose_name_plural': 'attachments',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='ProblemPackage',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('package_file', oioioi.filetracker.fields.FileField(upload_to=oioioi.problems.models._make_package_filename, verbose_name='package')),
                ('problem_name', models.CharField(blank=True, max_length=30, null=True, verbose_name='problem name', validators=[django.core.validators.RegexValidator(re.compile('^[-a-zA-Z0-9_]+$'), "Enter a valid 'slug' consisting of letters, numbers, underscores or hyphens.", 'invalid')])),
                ('celery_task_id', models.CharField(max_length=50, unique=True, null=True, blank=True)),
                ('info', models.CharField(max_length=1000, null=True, verbose_name='Package information', blank=True)),
                ('traceback', oioioi.filetracker.fields.FileField(upload_to=oioioi.problems.models._make_package_filename, null=True, verbose_name='traceback', blank=True)),
                ('status', oioioi.base.fields.EnumField(default=b'?', max_length=64, verbose_name='status', choices=[(b'?', 'Pending problem package'), (b'OK', 'Uploaded'), (b'ERR', 'Error')])),
                ('creation_date', models.DateTimeField(default=django.utils.timezone.now)),
                ('contest', models.ForeignKey(verbose_name='contest', blank=True, to='contests.Contest', null=True)),
                ('created_by', models.ForeignKey(verbose_name='created by', blank=True, to=settings.AUTH_USER_MODEL, null=True)),
                ('problem', models.ForeignKey(verbose_name='problem', blank=True, to='problems.Problem', null=True)),
            ],
            options={
                'ordering': ['-creation_date'],
                'verbose_name': 'problem package',
                'verbose_name_plural': 'problem packages',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='ProblemStatement',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('language', models.CharField(max_length=6, null=True, verbose_name='language code', blank=True)),
                ('content', oioioi.filetracker.fields.FileField(upload_to=oioioi.problems.models.make_problem_filename, verbose_name='content')),
                ('problem', models.ForeignKey(related_name='statements', to='problems.Problem')),
            ],
            options={
                'verbose_name': 'problem statement',
                'verbose_name_plural': 'problem statements',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='ContestProblemPackage',
            fields=[
            ],
            options={
                'verbose_name': 'Contest Problem Package',
                'proxy': True,
            },
            bases=('problems.problempackage',),
        ),
    ]
