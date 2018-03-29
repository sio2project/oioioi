# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('forum', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='post',
            name='reported_by',
            field=models.ForeignKey(related_name='post_user_reported', to=settings.AUTH_USER_MODEL, null=True),
            preserve_default=True,
        ),
    ]
