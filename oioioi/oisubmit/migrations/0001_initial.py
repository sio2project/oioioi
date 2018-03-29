# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('contests', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='OISubmitExtraData',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('localtime', models.DateTimeField(null=True, verbose_name='local time', blank=True)),
                ('siotime', models.DateTimeField(null=True, verbose_name='sio time', blank=True)),
                ('servertime', models.DateTimeField(null=True, verbose_name='server time', blank=True)),
                ('received_suspected', models.BooleanField(default=False, verbose_name='received suspected')),
                ('comments', models.CharField(max_length=255)),
                ('submission', models.OneToOneField(to='contests.Submission')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
    ]
