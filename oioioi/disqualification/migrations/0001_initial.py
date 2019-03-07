# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import django.core.validators
from django.conf import settings
from django.db import migrations, models

import oioioi.base.utils.validators


class Migration(migrations.Migration):

    dependencies = [
        ('contests', '0002_auto_20141219_1346'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Disqualification',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('title', models.CharField(max_length=255, verbose_name='title', validators=[django.core.validators.MaxLengthValidator(255), oioioi.base.utils.validators.validate_whitespaces])),
                ('content', models.TextField(verbose_name='content')),
                ('guilty', models.BooleanField(default=True)),
                ('contest', models.ForeignKey(verbose_name='contest', to='contests.Contest', on_delete=models.CASCADE)),
                ('submission', models.ForeignKey(verbose_name='submission', blank=True, to='contests.Submission', null=True, on_delete=models.CASCADE)),
                ('user', models.ForeignKey(verbose_name='user', to=settings.AUTH_USER_MODEL, on_delete=models.CASCADE)),
            ],
            options={
                'verbose_name': 'disqualification',
                'verbose_name_plural': 'disqualifications',
            },
            bases=(models.Model,),
        ),
    ]
