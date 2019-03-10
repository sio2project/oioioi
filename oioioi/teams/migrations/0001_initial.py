# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import django.core.validators
from django.conf import settings
from django.db import migrations, models

import oioioi.base.fields


class Migration(migrations.Migration):

    dependencies = [
        ('auth', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('contests', '0002_auto_20141219_1346'),
    ]

    operations = [
        migrations.CreateModel(
            name='Team',
            fields=[
                ('name', models.CharField(max_length=50, verbose_name='team name')),
                ('login', models.CharField(max_length=50, verbose_name='login')),
                ('user', models.OneToOneField(primary_key=True, serialize=False, to=settings.AUTH_USER_MODEL, verbose_name='user', on_delete=models.CASCADE)),
                ('join_key', models.CharField(max_length=40)),
                ('contest', models.ForeignKey(to='contests.Contest', on_delete=models.CASCADE)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='TeamMembership',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('team', models.ForeignKey(related_name='members', to='teams.Team', on_delete=models.CASCADE)),
                ('user', models.ForeignKey(to=settings.AUTH_USER_MODEL, on_delete=models.CASCADE)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='TeamsConfig',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('enabled', models.BooleanField(default=False)),
                ('max_team_size', models.IntegerField(default=3, validators=[django.core.validators.MinValueValidator(1)])),
                ('modify_begin_date', models.DateTimeField(null=True, verbose_name='team modification begin date', blank=True)),
                ('modify_end_date', models.DateTimeField(null=True, verbose_name='team modification end date', blank=True)),
                ('teams_list_visible', oioioi.base.fields.EnumField(default=b'NO', max_length=64, verbose_name='teams list visibility', choices=[(b'PUBLIC', 'Visible for all'), (b'YES', 'Visible only for registered users'), (b'NO', 'Not visible')])),
                ('contest', models.OneToOneField(to='contests.Contest', on_delete=models.CASCADE)),
            ],
            options={
                'verbose_name': 'teams configuration',
                'verbose_name_plural': 'teams configurations',
            },
            bases=(models.Model,),
        ),
        migrations.AlterUniqueTogether(
            name='teammembership',
            unique_together=set([('user', 'team')]),
        ),
    ]
