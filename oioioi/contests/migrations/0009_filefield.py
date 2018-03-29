# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models

import oioioi.contests.models
import oioioi.filetracker.fields

# Each field appears two times, because otherwise the migration doesn't work:
# https://code.djangoproject.com/ticket/25866

class Migration(migrations.Migration):

    dependencies = [
        ('contests', '0008_auto_20170424_1623'),
    ]

    operations = [
        migrations.AlterField(
            model_name='contestattachment',
            name='content',
            field=oioioi.filetracker.fields.FileField(
                upload_to=oioioi.contests.models.make_contest_filename,
                verbose_name='content',
                max_length=256),
        ),
        migrations.AlterField(
            model_name='contestattachment',
            name='content',
            field=oioioi.filetracker.fields.FileField(
                upload_to=oioioi.contests.models.make_contest_filename,
                verbose_name='content',
                max_length=255),
        ),
    ]
