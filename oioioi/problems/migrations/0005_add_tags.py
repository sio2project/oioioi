# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import re
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
        ('problems', '0004_problem_main_problem_instance'),
    ]

    operations = [
        migrations.CreateModel(
            name='Tag',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(unique=True, max_length=20, verbose_name='name', validators=[django.core.validators.MinLengthValidator(3), django.core.validators.MaxLengthValidator(20), django.core.validators.RegexValidator(re.compile('^[-a-zA-Z0-9_]+$'), "Enter a valid 'slug' consisting of letters, numbers, underscores or hyphens.", 'invalid')])),
            ],
            options={
                'verbose_name': 'tag',
                'verbose_name_plural': 'tags',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='TagThrough',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('problem', models.ForeignKey(to='problems.Problem')),
                ('tag', models.ForeignKey(to='problems.Tag')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.AlterUniqueTogether(
            name='tagthrough',
            unique_together=set([('problem', 'tag')]),
        ),
        migrations.AddField(
            model_name='tag',
            name='problems',
            field=models.ManyToManyField(to='problems.Problem', through='problems.TagThrough'),
            preserve_default=True,
        ),
        migrations.CreateModel(
            name='MainProblemInstance',
            fields=[
            ],
            options={
                'proxy': True,
            },
            bases=('contests.probleminstance',),
        ),
    ]
