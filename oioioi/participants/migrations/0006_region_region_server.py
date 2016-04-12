# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('participants', '0005_fixup_region'),
    ]

    operations = [
        migrations.AddField(
            model_name='region',
            name='region_server',
            field=models.CharField(help_text='IP address or hostname of the regional server', max_length=255, null=True, verbose_name='Region server', blank=True),
        ),
    ]
