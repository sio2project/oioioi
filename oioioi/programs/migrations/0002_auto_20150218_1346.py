# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import oioioi.base.fields


class Migration(migrations.Migration):

    dependencies = [
        ('programs', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='test',
            name='is_active',
            field=models.BooleanField(default=True),
            preserve_default=True,
        ),
    ]
