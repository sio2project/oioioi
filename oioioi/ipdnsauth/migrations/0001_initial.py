# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='DnsToUser',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('dns_name', models.CharField(unique=True, max_length=255, verbose_name='DNS hostname')),
                ('user', models.ForeignKey(to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'DNS autoauth mapping',
                'verbose_name_plural': 'DNS autoauth mappings',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='IpToUser',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('ip_addr', models.GenericIPAddressField(unique=True, verbose_name='IP address', unpack_ipv4=True)),
                ('user', models.ForeignKey(to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'IP autoauth mapping',
                'verbose_name_plural': 'IP autoauth mappings',
            },
            bases=(models.Model,),
        ),
    ]
