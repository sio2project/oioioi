# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('participants', '0006_region_region_server'),
    ]

    operations = [
        migrations.AlterField(
            model_name='region',
            name='contest',
            field=models.ForeignKey(related_name='regions', to='contests.Contest', on_delete=models.CASCADE),
        ),
    ]
