# -*- coding: utf-8 -*-
# Generated by Django 1.10.8 on 2019-06-15 18:43
# ADJUSTED manually, see part1 file
from __future__ import unicode_literals

from django.db import migrations, models
from django.db.models import Case, When, Value


def is_public_to_visibility(apps, schema_editor):
    Problem = apps.get_model('problems', 'Problem')
    db_alias = schema_editor.connection.alias
    Problem.objects.using(db_alias).all().update(
        visibility=Case(
            When(is_public=True, then=Value('PU')),  # Public
            default=Value('FR')  # Friends
        )
    )


def visibility_to_is_public(apps, schema_editor):
    Problem = apps.get_model('problems', 'Problem')
    db_alias = schema_editor.connection.alias
    Problem.objects.using(db_alias).all().update(
        is_public=Case(
            When(visibility='PU', then=Value(True)),  # Public
            default=Value(False)  # Other, we lose distinction: Private, Friends
        )
    )


class Migration(migrations.Migration):

    dependencies = [
        ('problems', '0014_visibility_part1'),
    ]

    operations = [
        migrations.RunPython(is_public_to_visibility, visibility_to_is_public),
    ]
