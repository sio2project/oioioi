# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models

import oioioi.filetracker.fields
import oioioi.problems.models

# Each field appears two times, because otherwise the migration doesn't work:
# https://code.djangoproject.com/ticket/25866

class Migration(migrations.Migration):

    dependencies = [
        ('problems', '0007_auto_20161214_1411'),
    ]

    operations = [
        migrations.AlterField(
            model_name='problemattachment',
            name='content',
            field=oioioi.filetracker.fields.FileField(
                upload_to=oioioi.problems.models.make_problem_filename,
                verbose_name='content',
                max_length=256),
        ),
        migrations.AlterField(
            model_name='problemattachment',
            name='content',
            field=oioioi.filetracker.fields.FileField(
                upload_to=oioioi.problems.models.make_problem_filename,
                verbose_name='content',
                max_length=255),
        ),
        migrations.AlterField(
            model_name='problempackage',
            name='package_file',
            field=oioioi.filetracker.fields.FileField(
                upload_to=oioioi.problems.models._make_package_filename,
                verbose_name='package',
                max_length=256),
        ),
        migrations.AlterField(
            model_name='problempackage',
            name='package_file',
            field=oioioi.filetracker.fields.FileField(
                upload_to=oioioi.problems.models._make_package_filename,
                verbose_name='package',
                max_length=255),
        ),
        migrations.AlterField(
            model_name='problempackage',
            name='traceback',
            field=oioioi.filetracker.fields.FileField(
                upload_to=oioioi.problems.models._make_package_filename,
                verbose_name='traceback', null=True, blank=True,
                max_length=256),
        ),
        migrations.AlterField(
            model_name='problempackage',
            name='traceback',
            field=oioioi.filetracker.fields.FileField(
                upload_to=oioioi.problems.models._make_package_filename,
                verbose_name='traceback', null=True, blank=True,
                max_length=255),
        ),
        migrations.AlterField(
            model_name='problemstatement',
            name='content',
            field=oioioi.filetracker.fields.FileField(
                upload_to=oioioi.problems.models.make_problem_filename,
                verbose_name='content',
                max_length=256),
        ),
        migrations.AlterField(
            model_name='problemstatement',
            name='content',
            field=oioioi.filetracker.fields.FileField(
                upload_to=oioioi.problems.models.make_problem_filename,
                verbose_name='content',
                max_length=255),
        ),
    ]
