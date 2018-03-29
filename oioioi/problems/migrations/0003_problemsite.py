# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('problems', '0002_auto_20150414_2326'),
    ]

    operations = [
        migrations.CreateModel(
            name='ProblemSite',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('url_key', models.CharField(unique=True, max_length=40)),
                ('problem', models.OneToOneField(to='problems.Problem')),
            ],
            options={
                'verbose_name': 'problem site',
                'verbose_name_plural': 'problem sites',
            },
            bases=(models.Model,),
        ),
    ]
