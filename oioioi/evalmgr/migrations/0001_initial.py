# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import django.utils.timezone
from django.db import migrations, models

import oioioi.base.fields


class Migration(migrations.Migration):

    dependencies = [
        ('contests', '0007_auto_20161214_1411'),
    ]

    operations = [
        migrations.CreateModel(
            name='QueuedJob',
            fields=[
                ('job_id', models.CharField(max_length=50, serialize=False, primary_key=True)),
                ('state', oioioi.base.fields.EnumField(default=b'QUEUED', max_length=64)),
                ('creation_date', models.DateTimeField(default=django.utils.timezone.now)),
                ('celery_task_id', models.CharField(max_length=50, unique=True, null=True, blank=True)),
                ('submission', models.ForeignKey(to='contests.Submission', null=True, on_delete=models.CASCADE)),
            ],
            options={
                'ordering': ['pk'],
                'verbose_name': 'Queued job',
                'verbose_name_plural': 'Queued jobs',
            },
        ),
        migrations.CreateModel(
            name='SavedEnviron',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('environ', models.TextField(help_text='JSON-encoded evaluation environ')),
                ('save_time', models.DateTimeField(help_text='Time and date when the environ was saved', auto_now=True)),
                ('queued_job', models.OneToOneField(to='evalmgr.QueuedJob')),
            ],
        ),
        migrations.CreateModel(
            name='ContestQueuedJob',
            fields=[
            ],
            options={
                'verbose_name': 'Contest Queued Jobs',
                'proxy': True,
            },
            bases=('evalmgr.queuedjob',),
        ),
    ]
