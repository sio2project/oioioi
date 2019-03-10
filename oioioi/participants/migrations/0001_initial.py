# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations, models

import oioioi.base.fields
import oioioi.participants.fields


class Migration(migrations.Migration):

    dependencies = [
        ('contests', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Participant',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('status', oioioi.base.fields.EnumField(default=b'ACTIVE', max_length=64, choices=[(b'ACTIVE', 'Active'), (b'BANNED', 'Banned')])),
                ('anonymous', models.BooleanField(default=False)),
                ('contest', models.ForeignKey(to='contests.Contest', on_delete=models.CASCADE)),
                ('user', models.ForeignKey(to=settings.AUTH_USER_MODEL, on_delete=models.CASCADE)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='TestRegistration',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=255)),
                ('participant', oioioi.participants.fields.OneToOneBothHandsCascadingParticipantField(related_name='participants_testregistration', to='participants.Participant', on_delete=models.CASCADE)),
            ],
            options={
                'abstract': False,
            },
            bases=(models.Model,),
        ),
        migrations.AlterUniqueTogether(
            name='participant',
            unique_together=set([('contest', 'user')]),
        ),
    ]
