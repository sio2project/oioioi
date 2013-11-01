# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import oioioi.mailsubmit.models
import oioioi.filetracker.fields
import django.utils.timezone
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('contests', '0002_auto_20141219_1346'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='MailSubmission',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('date', models.DateTimeField(default=django.utils.timezone.now, db_index=True, verbose_name='date', blank=True)),
                ('source_file', oioioi.filetracker.fields.FileField(upload_to=oioioi.mailsubmit.models.make_submission_filename)),
                ('accepted_by', models.ForeignKey(related_name='+', verbose_name='accepted by', blank=True, to=settings.AUTH_USER_MODEL, null=True)),
                ('problem_instance', models.ForeignKey(verbose_name='problem', to='contests.ProblemInstance')),
                ('submission', models.ForeignKey(verbose_name='related submission', blank=True, to='contests.Submission', null=True)),
                ('user', models.ForeignKey(verbose_name='user', blank=True, to=settings.AUTH_USER_MODEL, null=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='MailSubmissionConfig',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('enabled', models.BooleanField(default=False, verbose_name='enabled')),
                ('start_date', models.DateTimeField(verbose_name='start date')),
                ('end_date', models.DateTimeField(null=True, verbose_name='end date', blank=True)),
                ('printout_text', models.TextField(default='This document confirms that you have uploaded a file for postal submission on our server. To have this file judged, send this document by mail to us.', help_text='LaTeX-formatted text to show on the printed document sent by regular post; usually contains the instruction on how, where and when to send it.', verbose_name='printout text')),
                ('contest', models.OneToOneField(related_name='mail_submission_config', to='contests.Contest')),
            ],
            options={
                'verbose_name': 'postal submission configuration',
                'verbose_name_plural': 'postal submission configurations',
            },
            bases=(models.Model,),
        ),
    ]
