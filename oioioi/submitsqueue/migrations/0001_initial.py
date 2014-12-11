# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.utils.timezone
import oioioi.base.fields


class Migration(migrations.Migration):

    dependencies = [
        ('contests', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='QueuedSubmit',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('state', oioioi.base.fields.EnumField(default=b'QUEUED', max_length=64, choices=[(b'QUEUED', 'Queued'), (b'PROGRESS', 'In progress'), (b'PROGRESS-RESUMED', 'In progress (resumed)'), (b'CANCELLED', 'Cancelled'), (b'WAITING', 'Waiting'), (b'SUSPENDED', 'Suspended')])),
                ('creation_date', models.DateTimeField(default=django.utils.timezone.now)),
                ('celery_task_id', models.CharField(max_length=50, unique=True, null=True, blank=True)),
                ('submission', models.ForeignKey(to='contests.Submission')),
            ],
            options={
                'ordering': ['pk'],
                'verbose_name': 'Queued Submit',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='ContestQueuedSubmit',
            fields=[
            ],
            options={
                'verbose_name': 'Contest Queued Submit',
                'proxy': True,
            },
            bases=('submitsqueue.queuedsubmit',),
        ),
    ]
