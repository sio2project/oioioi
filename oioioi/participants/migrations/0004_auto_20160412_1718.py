# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import re

import django.core.validators
import django.db.models.deletion
from django.db import migrations, models

import oioioi.participants.fields


class Migration(migrations.Migration):

    dependencies = [
        ('contests', '0005_auto_20150531_2248'),
        ('participants', '0003_openregistration'),
    ]

    operations = [
        migrations.CreateModel(
            name='OnsiteRegistration',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('number', models.IntegerField(verbose_name='number')),
                ('local_number', models.IntegerField(verbose_name='local number')),
                ('participant', oioioi.participants.fields.OneToOneBothHandsCascadingParticipantField(related_name='participants_onsiteregistration', to='participants.Participant', on_delete=models.CASCADE)),
                ('region', models.IntegerField(verbose_name='region', null=True)),
            ],
        ),
        migrations.CreateModel(
            name='Region',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('short_name', models.CharField(max_length=10, validators=[django.core.validators.RegexValidator(re.compile(b'^[a-z0-9_-]+$'), "Enter a valid 'slug' consisting of lowercase letters, numbers, underscores or hyphens.", b'invalid')])),
                ('name', models.CharField(max_length=255)),
                ('contest', models.ForeignKey(to='contests.Contest', on_delete=models.CASCADE)),
            ],
        ),
        migrations.AlterUniqueTogether(
            name='region',
            unique_together=set([('contest', 'short_name')]),
        ),
        migrations.AlterUniqueTogether(
            name='onsiteregistration',
            unique_together=set([('region', 'local_number')]),
        ),
    ]
