# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('problems', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='problem',
            name='author',
            field=models.ForeignKey(verbose_name='author', blank=True, to=settings.AUTH_USER_MODEL, null=True, on_delete=models.CASCADE),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='problem',
            name='is_public',
            field=models.BooleanField(default=False, verbose_name='is public'),
            preserve_default=True,
        ),
    ]
