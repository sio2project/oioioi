# Generated by Django 3.2.16 on 2023-01-30 16:01

import datetime
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('teachers', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='teacher',
            name='join_date',
            field=models.DateField(auto_now_add=True, default=datetime.date(1983, 1, 1)),
            preserve_default=False,
        ),
    ]
