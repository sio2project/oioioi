# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='ExclusivenessConfig',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('enabled', models.BooleanField(default=True, verbose_name='enabled')),
                ('start_date', models.DateTimeField(default=django.utils.timezone.now, verbose_name='start date')),
                ('end_date', models.DateTimeField(null=True, verbose_name='end date', blank=True)),
            ],
            options={
                'verbose_name': 'exclusiveness config',
                'verbose_name_plural': 'exclusiveness configs',
            },
            bases=(models.Model,),
        ),
    ]
