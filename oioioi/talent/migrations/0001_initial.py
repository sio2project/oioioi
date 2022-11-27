# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models

import oioioi.participants.fields


class Migration(migrations.Migration):

    dependencies = [
        ('participants', '0002_auto_20150420_2002'),
    ]

    operations = [
        migrations.CreateModel(
            name='TalentRegistration',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('participant', oioioi.participants.fields.OneToOneBothHandsCascadingParticipantField(related_name='participants_talentregistration', to='participants.Participant', on_delete=models.CASCADE)),
                ('group', models.CharField(max_length=1, verbose_name='Group', default="")),
            ],
            options={
                'abstract': False,
            },
            bases=(models.Model,),
        ),
    ]
