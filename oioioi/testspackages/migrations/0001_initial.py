# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import django.core.validators
from django.db import migrations, models

import oioioi.filetracker.fields
import oioioi.problems.models


class Migration(migrations.Migration):

    dependencies = [
        ('problems', '0001_initial'),
        ('programs', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='TestsPackage',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(help_text='File name can only contain letters, digits, - and _. It should not contain file extension such as .zip, .tgz, etc.', max_length=30, verbose_name='file name', validators=[django.core.validators.RegexValidator(b'^[0-9a-zA-Z\\-_]+$', 'Name can only contain letters, digits, - and _.')])),
                ('description', models.TextField(blank=True)),
                ('package', oioioi.filetracker.fields.FileField(upload_to=oioioi.problems.models.make_problem_filename, null=True, verbose_name='package', blank=True)),
                ('publish_date', models.DateTimeField(help_text='If the date is left blank, the package will never be visible for participants of the contest.', null=True, verbose_name='publish date', blank=True)),
                ('problem', models.ForeignKey(to='problems.Problem', on_delete=models.CASCADE)),
                ('tests', models.ManyToManyField(to='programs.Test')),
            ],
            options={
                'verbose_name': 'tests package',
                'verbose_name_plural': 'tests packages',
            },
            bases=(models.Model,),
        ),
    ]
