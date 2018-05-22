# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('newsfeed', '0003_news_data_to_newslanguageversion'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='news',
            name='content',
        ),
        migrations.RemoveField(
            model_name='news',
            name='title',
        ),
    ]
