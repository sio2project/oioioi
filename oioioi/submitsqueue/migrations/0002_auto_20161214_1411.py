# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('submitsqueue', '0001_initial'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='queuedsubmit',
            options={'ordering': ['pk'], 'verbose_name': 'Queued submission', 'verbose_name_plural': 'Queued submissions'},
        ),
    ]
