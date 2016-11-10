# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('contests', '0005_auto_20150531_2248'),
    ]

    operations = [
        migrations.AddField(
            model_name='contestattachment',
            name='pub_date',
            field=models.DateTimeField(default=None, null=True, blank=True, verbose_name='publication date'),
        ),
    ]
