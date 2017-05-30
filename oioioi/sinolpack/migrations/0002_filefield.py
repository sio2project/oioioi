# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import oioioi.problems.models
import oioioi.filetracker.fields

# Each field appears two times, because otherwise the migration doesn't work:
# https://code.djangoproject.com/ticket/25866

class Migration(migrations.Migration):

    dependencies = [
        ('sinolpack', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='extrafile',
            name='file',
            field=oioioi.filetracker.fields.FileField(
                upload_to=oioioi.problems.models.make_problem_filename,
                max_length=256),
        ),
        migrations.AlterField(
            model_name='extrafile',
            name='file',
            field=oioioi.filetracker.fields.FileField(
                upload_to=oioioi.problems.models.make_problem_filename,
                max_length=255),
        ),
    ]
