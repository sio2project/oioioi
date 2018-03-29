# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models

import oioioi.filetracker.fields
import oioioi.problems.models


class Migration(migrations.Migration):

    dependencies = [
        ('problems', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='ExtraConfig',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('config', models.TextField(verbose_name='config')),
                ('problem', models.OneToOneField(to='problems.Problem')),
            ],
            options={
                'verbose_name': "sinolpack's configuration",
                'verbose_name_plural': "sinolpack's configurations",
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='ExtraFile',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=255, verbose_name='name')),
                ('file', oioioi.filetracker.fields.FileField(upload_to=oioioi.problems.models.make_problem_filename)),
                ('problem', models.ForeignKey(to='problems.Problem')),
            ],
            options={
                'verbose_name': "sinolpack's extra file",
                'verbose_name_plural': "sinolpack's extra files",
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='OriginalPackage',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('problem', models.ForeignKey(to='problems.Problem')),
                ('problem_package', models.ForeignKey(blank=True, to='problems.ProblemPackage', null=True)),
            ],
            options={
                'verbose_name': 'original problem package',
                'verbose_name_plural': 'original problem packages',
            },
            bases=(models.Model,),
        ),
    ]
