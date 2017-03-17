# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('zeus', '0003_auto_20170213_2116'),
    ]

    operations = [
        migrations.DeleteModel(
            name='ZeusAsyncJob',
        ),
    ]
