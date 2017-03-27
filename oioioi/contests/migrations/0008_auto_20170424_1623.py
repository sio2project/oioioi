# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
        ('contests', '0007_auto_20161214_1411'),
    ]

    operations = [
        migrations.AddField(
            model_name='contest',
            name='judging_priority',
            field=models.IntegerField(default=10, help_text='Contest with higher judging priority is always judged before contest with lower judging priority.', verbose_name='judging priority'),
        ),
        migrations.AddField(
            model_name='contest',
            name='judging_weight',
            field=models.IntegerField(default=1000, help_text='If some contests have the same judging priority, the judging resources are allocated proportionally to their weights.', verbose_name='judging weight', validators=[django.core.validators.MinValueValidator(1)]),
        ),
    ]
