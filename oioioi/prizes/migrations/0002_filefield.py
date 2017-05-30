# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import oioioi.prizes.models
import oioioi.filetracker.fields

# Each field appears two times, because otherwise the migration doesn't work:
# https://code.djangoproject.com/ticket/25866

class Migration(migrations.Migration):

    dependencies = [
        ('prizes', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='prizegiving',
            name='report',
            field=oioioi.filetracker.fields.FileField(
                upload_to=oioioi.prizes.models._make_report_filename,
                null=True, editable=False,
                max_length=256),
        ),
        migrations.AlterField(
            model_name='prizegiving',
            name='report',
            field=oioioi.filetracker.fields.FileField(
                upload_to=oioioi.prizes.models._make_report_filename,
                null=True, editable=False,
                max_length=255),
        ),
    ]
