# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('problems', '0004_problem_main_problem_instance'),
        ('portals', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='node',
            name='problems_in_content',
            field=models.ManyToManyField(to='problems.Problem', blank=True),
            preserve_default=True,
        ),
    ]
