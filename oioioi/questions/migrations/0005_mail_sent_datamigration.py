# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


def toggle_mail_sent(apps, schema_editor):
    Message = apps.get_model("questions", "Message")
    for msg in Message.objects.all():
        msg.mail_sent = True
        msg.save()

class Migration(migrations.Migration):

    dependencies = [
        ('questions', '0004_message_mail_sent'),
    ]

    operations = [
        migrations.RunPython(toggle_mail_sent)
    ]
