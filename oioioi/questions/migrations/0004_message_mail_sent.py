# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('questions', '0003_questionsubscription'),
    ]

    operations = [
        migrations.AddField(
            model_name='message',
            name='mail_sent',
            field=models.BooleanField(default=False, verbose_name='mail notification sent'),
        )
    ]
