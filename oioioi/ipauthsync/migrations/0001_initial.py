# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('participants', '0007_auto_20160412_2050'),
        ('contests', '0001_initial'),
        ('ipdnsauth', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='IpAuthSyncConfig',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('enabled', models.BooleanField(default=True, verbose_name='enabled')),
                ('start_date', models.DateTimeField(default=django.utils.timezone.now, verbose_name='start date')),
                ('end_date', models.DateTimeField(verbose_name='end date')),
                ('region_server_mysql_user', models.CharField(default=b'oi', max_length=255, verbose_name='MySQL username')),
                ('region_server_mysql_pass', models.CharField(max_length=255, verbose_name='MySQL password', blank=True)),
                ('region_server_mysql_db', models.CharField(default=b'oi', max_length=255, verbose_name='MySQL database name')),
                ('contest', models.OneToOneField(to='contests.Contest')),
            ],
            options={
                'verbose_name': 'IP authentication sync config',
                'verbose_name_plural': 'IP authentication sync configs',
            },
        ),
        migrations.CreateModel(
            name='IpAuthSyncedUser',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('entry', models.OneToOneField(to='ipdnsauth.IpToUser')),
            ],
        ),
        migrations.CreateModel(
            name='IpAuthSyncRegionMessages',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('warnings', models.TextField(verbose_name='Warnings', blank=True)),
                ('mapping', models.TextField(verbose_name='Mapping', blank=True)),
                ('region', models.OneToOneField(to='participants.Region')),
            ],
            options={
                'verbose_name': 'IP authentication sync messages',
                'verbose_name_plural': 'IP authentication sync messages',
            },
        ),
    ]
