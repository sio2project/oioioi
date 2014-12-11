# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('contests', '0001_initial'),
        ('problems', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='ScoreReveal',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('submission', models.OneToOneField(related_name='revealed', verbose_name='submission', to='contests.Submission')),
            ],
            options={
                'verbose_name': 'score reveal',
                'verbose_name_plural': 'score reveals',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='ScoreRevealConfig',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('reveal_limit', models.IntegerField(verbose_name='reveal limit')),
                ('disable_time', models.IntegerField(null=True, verbose_name='disable for last minutes of the round', blank=True)),
                ('problem', models.OneToOneField(related_name='scores_reveal_config', verbose_name='problem', to='problems.Problem')),
            ],
            options={
                'verbose_name': 'score reveal config',
                'verbose_name_plural': 'score reveal configs',
            },
            bases=(models.Model,),
        ),
    ]
