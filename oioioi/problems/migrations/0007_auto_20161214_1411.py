# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import re

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('problems', '0006_default_values_for_problem'),
    ]

    operations = [
        migrations.AlterField(
            model_name='problem',
            name='short_name',
            field=models.CharField(max_length=30, verbose_name='short name', validators=[django.core.validators.RegexValidator(re.compile('^[-a-zA-Z0-9_]+\\Z'), "Enter a valid 'slug' consisting of letters, numbers, underscores or hyphens.", 'invalid')]),
        ),
        migrations.AlterField(
            model_name='problempackage',
            name='problem_name',
            field=models.CharField(blank=True, max_length=30, null=True, verbose_name='problem name', validators=[django.core.validators.RegexValidator(re.compile('^[-a-zA-Z0-9_]+\\Z'), "Enter a valid 'slug' consisting of letters, numbers, underscores or hyphens.", 'invalid')]),
        ),
        migrations.AlterField(
            model_name='tag',
            name='name',
            field=models.CharField(unique=True, max_length=20, verbose_name='name', validators=[django.core.validators.MinLengthValidator(3), django.core.validators.MaxLengthValidator(20), django.core.validators.RegexValidator(re.compile('^[-a-zA-Z0-9_]+\\Z'), "Enter a valid 'slug' consisting of letters, numbers, underscores or hyphens.", 'invalid')]),
        ),
    ]
