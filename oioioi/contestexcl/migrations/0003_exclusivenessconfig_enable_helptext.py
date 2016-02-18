# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('contestexcl', '0002_exclusivenessconfig_contest'),
    ]

    operations = [
        migrations.AlterField(
            model_name='exclusivenessconfig',
            name='enabled',
            field=models.BooleanField(default=True, help_text="Caution! If you'll disable exclusiveness and you are not superadmin you won't be able to enable it again!", verbose_name='enabled'),
        ),
    ]
