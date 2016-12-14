# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('oi', '0002_auto_20160412_1720'),
    ]

    operations = [
        migrations.AlterField(
            model_name='school',
            name='email',
            field=models.EmailField(max_length=254, verbose_name='email', blank=True),
        ),
    ]
