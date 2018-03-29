# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models

import oioioi.filetracker.fields
import oioioi.testrun.models

# Each field appears two times, because otherwise the migration doesn't work:
# https://code.djangoproject.com/ticket/25866

class Migration(migrations.Migration):

    dependencies = [
        ('testrun', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='testrunprogramsubmission',
            name='input_file',
            field=oioioi.filetracker.fields.FileField(
                upload_to=oioioi.testrun.models.make_custom_input_filename,
                max_length=256),
        ),
        migrations.AlterField(
            model_name='testrunprogramsubmission',
            name='input_file',
            field=oioioi.filetracker.fields.FileField(
                upload_to=oioioi.testrun.models.make_custom_input_filename,
                max_length=255),
        ),
        migrations.AlterField(
            model_name='testrunreport',
            name='output_file',
            field=oioioi.filetracker.fields.FileField(
                upload_to=oioioi.testrun.models.make_custom_output_filename,
                max_length=256),
        ),
        migrations.AlterField(
            model_name='testrunreport',
            name='output_file',
            field=oioioi.filetracker.fields.FileField(
                upload_to=oioioi.testrun.models.make_custom_output_filename,
                max_length=255),
        ),
    ]
