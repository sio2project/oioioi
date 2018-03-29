# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models

import oioioi.filetracker.fields
import oioioi.problems.models
import oioioi.programs.models

# Each field appears two times, because otherwise the migration doesn't work:
# https://code.djangoproject.com/ticket/25866

class Migration(migrations.Migration):

    dependencies = [
        ('programs', '0004_auto_20161214_1411'),
    ]

    operations = [
        migrations.AlterField(
            model_name='modelsolution',
            name='source_file',
            field=oioioi.filetracker.fields.FileField(
                upload_to=oioioi.problems.models.make_problem_filename,
                verbose_name='source',
                max_length=256),
        ),
        migrations.AlterField(
            model_name='modelsolution',
            name='source_file',
            field=oioioi.filetracker.fields.FileField(
                upload_to=oioioi.problems.models.make_problem_filename,
                verbose_name='source',
                max_length=255),
        ),
        migrations.AlterField(
            model_name='outputchecker',
            name='exe_file',
            field=oioioi.filetracker.fields.FileField(
                upload_to=oioioi.problems.models.make_problem_filename,
                verbose_name='checker executable file', null=True, blank=True,
                max_length=256),
        ),
        migrations.AlterField(
            model_name='outputchecker',
            name='exe_file',
            field=oioioi.filetracker.fields.FileField(
                upload_to=oioioi.problems.models.make_problem_filename,
                verbose_name='checker executable file', null=True, blank=True,
                max_length=255),
        ),
        migrations.AlterField(
            model_name='programsubmission',
            name='source_file',
            field=oioioi.filetracker.fields.FileField(
                upload_to=oioioi.programs.models.make_submission_filename,
                max_length=256),
        ),
        migrations.AlterField(
            model_name='programsubmission',
            name='source_file',
            field=oioioi.filetracker.fields.FileField(
                upload_to=oioioi.programs.models.make_submission_filename,
                max_length=255),
        ),
        migrations.AlterField(
            model_name='test',
            name='input_file',
            field=oioioi.filetracker.fields.FileField(
                upload_to=oioioi.problems.models.make_problem_filename,
                verbose_name='input', null=True, blank=True,
                max_length=256),
        ),
        migrations.AlterField(
            model_name='test',
            name='input_file',
            field=oioioi.filetracker.fields.FileField(
                upload_to=oioioi.problems.models.make_problem_filename,
                verbose_name='input', null=True, blank=True,
                max_length=255),
        ),
        migrations.AlterField(
            model_name='test',
            name='output_file',
            field=oioioi.filetracker.fields.FileField(
                upload_to=oioioi.problems.models.make_problem_filename,
                verbose_name='output/hint', null=True, blank=True,
                max_length=256),
        ),
        migrations.AlterField(
            model_name='test',
            name='output_file',
            field=oioioi.filetracker.fields.FileField(
                upload_to=oioioi.problems.models.make_problem_filename,
                verbose_name='output/hint', null=True, blank=True,
                max_length=255),
        ),
        migrations.AlterField(
            model_name='testreport',
            name='output_file',
            field=oioioi.filetracker.fields.FileField(
                upload_to=oioioi.programs.models.make_output_filename,
                null=True, blank=True,
                max_length=256),
        ),
        migrations.AlterField(
            model_name='testreport',
            name='output_file',
            field=oioioi.filetracker.fields.FileField(
                upload_to=oioioi.programs.models.make_output_filename,
                null=True, blank=True,
                max_length=255),
        ),
    ]
