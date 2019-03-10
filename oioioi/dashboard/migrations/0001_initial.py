# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('contests', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='DashboardMessage',
            fields=[
                ('contest', models.OneToOneField(primary_key=True, serialize=False, to='contests.Contest', on_delete=models.CASCADE)),
                ('content', models.TextField(verbose_name='message', blank=True)),
            ],
            options={
                'verbose_name': 'dashboard message',
                'verbose_name_plural': 'dashboard messages',
            },
            bases=(models.Model,),
        ),
    ]
