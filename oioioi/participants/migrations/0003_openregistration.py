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
            name='OpenRegistration',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('terms_accepted', models.BooleanField(default=False, help_text='I declare that I have read the contest rules and the technical arrangements. I fully understand them and accept them unconditionally.', verbose_name='terms accepted')),
                ('participant', oioioi.participants.fields.OneToOneBothHandsCascadingParticipantField(related_name='participants_openregistration', to='participants.Participant', on_delete=models.CASCADE)),
            ],
            options={
                'abstract': False,
            },
            bases=(models.Model,),
        ),
    ]
