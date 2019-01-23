# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import django.core.validators
from django.db import migrations, models
import re


class Migration(migrations.Migration):
    dependencies = [
        ('portals', '0004_auto_20170523_0848'),
    ]

    operations = [
        migrations.AddField(
            model_name='portal',
            name='link_name',
            field=models.CharField(help_text='Shown in the URL.', max_length=40,
                                   null=True, unique=True,
                                   validators=[
                                       django.core.validators.RegexValidator(
                                           re.compile(b'^[a-z0-9_-]+$'),
                                           "Enter a valid 'slug' consisting of "
                                           "lowercase letters, numbers, "
                                           "underscores or hyphens.",
                                           b'invalid')]),
        ),
        migrations.AddField(
            model_name='portal',
            name='is_public',
            field=models.BooleanField(default=False, verbose_name='is public'),
        ),
        migrations.AddField(
            model_name='portal',
            name='short_description',
            field=models.CharField(default='My portal.', max_length=256,
                                   null=True, verbose_name='short description'),
        )
    ]
