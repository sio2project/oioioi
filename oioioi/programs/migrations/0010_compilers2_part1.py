# -*- coding: utf-8 -*-
# Generated by Django 1.10.8 on 2020-01-12 08:37
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('programs', '0009_compilers_part2'),
    ]

    operations = [
        migrations.AddField(
            model_name='problemcompiler',
            name='auto_created',
            field=models.BooleanField(default=False, editable=False),
        ),
    ]
