# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('contests', '0001_initial'),
        ('contestexcl', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='exclusivenessconfig',
            name='contest',
            field=models.OneToOneField(to='contests.Contest'),
            preserve_default=True,
        ),
    ]
