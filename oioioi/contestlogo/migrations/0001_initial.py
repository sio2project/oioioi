# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.utils.timezone
import oioioi.contestlogo.models
import oioioi.filetracker.fields


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='ContestIcon',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('image', oioioi.filetracker.fields.FileField(upload_to=oioioi.contestlogo.models.make_icon_filename, verbose_name='icon image')),
                ('updated_at', models.DateTimeField(default=django.utils.timezone.now)),
            ],
            options={
                'verbose_name': 'contest icon',
                'verbose_name_plural': 'contest icons',
            },
            bases=(models.Model,),
        ),
    ]
