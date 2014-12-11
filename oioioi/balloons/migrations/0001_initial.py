# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='BalloonDelivery',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('delivered', models.BooleanField(default=False, verbose_name='delivered')),
                ('first_accepted_solution', models.BooleanField(default=False, verbose_name='first accepted solution')),
            ],
            options={
                'ordering': ['id'],
                'verbose_name': 'balloon delivery',
                'verbose_name_plural': 'balloon deliveries',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='BalloonsDeliveryAccessData',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('access_key', models.CharField(max_length=16, verbose_name='access key')),
                ('valid_until', models.DateTimeField(null=True, verbose_name='valid until')),
            ],
            options={
                'verbose_name': 'balloons delivery access data',
                'verbose_name_plural': 'balloons delivery access data',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='BalloonsDisplay',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('ip_addr', models.GenericIPAddressField(unique=True, verbose_name='IP address', unpack_ipv4=True)),
            ],
            options={
                'verbose_name': 'balloons display',
                'verbose_name_plural': 'balloons displays',
            },
            bases=(models.Model,),
        ),
    ]
