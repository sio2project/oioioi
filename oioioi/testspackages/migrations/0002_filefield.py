# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models

import oioioi.filetracker.fields
import oioioi.problems.models

# Each field appears two times, because otherwise the migration doesn't work:
# https://code.djangoproject.com/ticket/25866

class Migration(migrations.Migration):

    dependencies = [
        ('testspackages', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='testspackage',
            name='package',
            field=oioioi.filetracker.fields.FileField(
                upload_to=oioioi.problems.models.make_problem_filename,
                verbose_name='package', null=True, blank=True,
                max_length=256),
        ),
        migrations.AlterField(
            model_name='testspackage',
            name='package',
            field=oioioi.filetracker.fields.FileField(
                upload_to=oioioi.problems.models.make_problem_filename,
                verbose_name='package', null=True, blank=True,
                max_length=255),
        ),
    ]
