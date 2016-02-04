# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='News',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('date', models.DateTimeField(auto_now_add=True, verbose_name='date')),
                ('title', models.CharField(max_length=255, verbose_name='title')),
                ('content', models.TextField(verbose_name='content')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
    ]
