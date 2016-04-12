# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import re
import django.db.models.deletion
import django.core.validators
import oioioi.participants.fields


class Migration(migrations.Migration):

    dependencies = [
        ('participants', '0004_auto_20160412_1718'),
    ]

    operations = [
        migrations.AlterField(
            model_name='onsiteregistration',
            name='region',
            field=models.ForeignKey(on_delete=django.db.models.deletion.SET_NULL, verbose_name='region', to='participants.Region', null=True),
        ),
    ]
