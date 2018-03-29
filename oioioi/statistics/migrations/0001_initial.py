# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('contests', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='StatisticsConfig',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('visible_to_users', models.BooleanField(default=False, verbose_name='visible to users')),
                ('visibility_date', models.DateTimeField(verbose_name='visibility date')),
                ('contest', models.OneToOneField(related_name='statistics_config', to='contests.Contest')),
            ],
            options={
                'verbose_name': 'statistics configuration',
                'verbose_name_plural': 'statistics configurations',
            },
            bases=(models.Model,),
        ),
    ]
