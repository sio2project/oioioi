# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('submitservice', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='submitservicetoken',
            name='user',
            field=models.OneToOneField(to=settings.AUTH_USER_MODEL, on_delete=models.CASCADE),
        ),
    ]
