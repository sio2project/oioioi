# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('contests', '0007_auto_20161214_1411'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('questions', '0002_message_pub_date'),
    ]

    operations = [
        migrations.CreateModel(
            name='QuestionSubscription',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('contest', models.ForeignKey(to='contests.Contest')),
                ('user', models.ForeignKey(to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
