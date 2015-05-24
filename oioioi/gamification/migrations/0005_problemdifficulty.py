# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('problems', '0004_problem_main_problem_instance'),
        ('gamification', '0004_auto_20150507_1434'),
    ]

    operations = [
        migrations.CreateModel(
            name='ProblemDifficulty',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('difficulty', models.SmallIntegerField(null=True, blank=True)),
                ('problem', models.OneToOneField(to='problems.Problem')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
    ]
