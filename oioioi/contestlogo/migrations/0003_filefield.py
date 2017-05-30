# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import oioioi.contestlogo.models
import oioioi.filetracker.fields

# Each field appears two times, because otherwise the migration doesn't work:
# https://code.djangoproject.com/ticket/25866

class Migration(migrations.Migration):

    dependencies = [
        ('contestlogo', '0002_auto_20141219_1346'),
    ]

    operations = [
        migrations.AlterField(
            model_name='contesticon',
            name='image',
            field=oioioi.filetracker.fields.FileField(
                upload_to=oioioi.contestlogo.models.make_icon_filename,
                verbose_name='icon image',
                max_length=256),
        ),
        migrations.AlterField(
            model_name='contesticon',
            name='image',
            field=oioioi.filetracker.fields.FileField(
                upload_to=oioioi.contestlogo.models.make_icon_filename,
                verbose_name='icon image',
                max_length=255),
        ),
        migrations.AlterField(
            model_name='contestlogo',
            name='image',
            field=oioioi.filetracker.fields.FileField(
                upload_to=oioioi.contestlogo.models.make_logo_filename,
                verbose_name='logo image',
                max_length=256),
        ),
        migrations.AlterField(
            model_name='contestlogo',
            name='image',
            field=oioioi.filetracker.fields.FileField(
                upload_to=oioioi.contestlogo.models.make_logo_filename,
                verbose_name='logo image',
                max_length=255),
        ),
    ]
