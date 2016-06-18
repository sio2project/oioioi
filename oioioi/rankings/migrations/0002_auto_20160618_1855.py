# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('rankings', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='ranking',
            name='serialized_data',
            field=models.BinaryField(null=True),
        ),
        migrations.AlterUniqueTogether(
            name='ranking',
            unique_together=set([('contest', 'key')]),
        ),
    ]
