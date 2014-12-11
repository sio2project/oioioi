# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('contests', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='VoluntarySolutionPublication',
            fields=[
                ('submission', models.OneToOneField(related_name='publication', primary_key=True, serialize=False, to='contests.Submission', verbose_name='submission')),
            ],
            options={
                'verbose_name': 'voluntary solution publication',
                'verbose_name_plural': 'voluntary solution publications',
            },
            bases=(models.Model,),
        ),
    ]
