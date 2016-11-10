# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('questions', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='message',
            name='pub_date',
            field=models.DateTimeField(default=None, null=True, blank=True, verbose_name='publication date'),
        ),
    ]
