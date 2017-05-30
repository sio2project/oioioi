# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import oioioi.mailsubmit.models
import oioioi.filetracker.fields

# Each field appears two times, because otherwise the migration doesn't work:
# https://code.djangoproject.com/ticket/25866

class Migration(migrations.Migration):

    dependencies = [
        ('mailsubmit', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='mailsubmission',
            name='source_file',
            field=oioioi.filetracker.fields.FileField(
                upload_to=oioioi.mailsubmit.models.make_submission_filename,
                max_length=256),
        ),
        migrations.AlterField(
            model_name='mailsubmission',
            name='source_file',
            field=oioioi.filetracker.fields.FileField(
                upload_to=oioioi.mailsubmit.models.make_submission_filename,
                max_length=255),
        ),
    ]
