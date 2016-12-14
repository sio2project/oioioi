# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import oioioi.programs.models


class Migration(migrations.Migration):

    dependencies = [
        ('programs', '0003_auto_20150420_2002'),
    ]

    operations = [
        migrations.AlterField(
            model_name='test',
            name='memory_limit',
            field=models.IntegerField(blank=True, null=True, verbose_name='memory limit (KiB)', validators=[oioioi.programs.models.validate_memory_limit]),
        ),
    ]
