# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models

import oioioi.base.fields


class Migration(migrations.Migration):

    dependencies = [
        ('participants', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='participant',
            name='status',
            field=oioioi.base.fields.EnumField(default=b'ACTIVE', max_length=64, choices=[(b'ACTIVE', 'Active'), (b'BANNED', 'Banned'), (b'DELETED', 'Account deleted')]),
            preserve_default=True,
        ),
    ]
