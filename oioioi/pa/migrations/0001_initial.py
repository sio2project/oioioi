# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models

import oioioi.base.fields
import oioioi.participants.fields


class Migration(migrations.Migration):

    dependencies = [
        ('participants', '0001_initial'),
        ('contests', '0002_auto_20141219_1346'),
    ]

    operations = [
        migrations.CreateModel(
            name='PAProblemInstanceData',
            fields=[
                ('problem_instance', models.OneToOneField(primary_key=True, serialize=False, to='contests.ProblemInstance', on_delete=models.CASCADE)),
                ('division', oioioi.base.fields.EnumField(max_length=64, verbose_name='Division', choices=[(b'A', 'Division A'), (b'B', 'Division B'), (b'NONE', 'None')])),
            ],
            options={
                'verbose_name': 'Division',
                'verbose_name_plural': 'Divisions',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='PARegistration',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('address', models.CharField(max_length=255, verbose_name='address')),
                ('postal_code', oioioi.base.fields.PostalCodeField(verbose_name='postal code')),
                ('city', models.CharField(max_length=100, verbose_name='city')),
                ('job', models.CharField(max_length=7, verbose_name='job or school kind', choices=[(b'PS', b'Szko\xc5\x82a podstawowa'), (b'MS', b'Gimnazjum'), (b'HS', b'Szko\xc5\x82a ponadgimnazjalna'), (b'OTH', b'Inne'), (b'AS', b'Szko\xc5\x82a wy\xc5\xbcsza - student'), (b'AD', b'Szko\xc5\x82a wy\xc5\xbcsza - doktorant'), (b'COM', b'Firma')])),
                ('job_name', models.CharField(max_length=255, verbose_name='job or school name')),
                ('t_shirt_size', models.CharField(max_length=7, verbose_name='t-shirt size', choices=[(b'S', b'S'), (b'M', b'M'), (b'L', b'L'), (b'XL', b'XL'), (b'XXL', b'XXL')])),
                ('newsletter', models.BooleanField(default=False, help_text='I want to receive the information about further editions of the contest.', verbose_name='newsletter')),
                ('terms_accepted', models.BooleanField(default=False, help_text='I declare that I have read the contest rules and the technical arrangements. I fully understand them and accept them unconditionally.', verbose_name='terms accepted')),
                ('participant', oioioi.participants.fields.OneToOneBothHandsCascadingParticipantField(related_name='pa_paregistration', to='participants.Participant', on_delete=models.CASCADE)),
            ],
            options={
                'abstract': False,
            },
            bases=(models.Model,),
        ),
    ]