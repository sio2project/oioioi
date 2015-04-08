# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('gamification', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='FriendProxy',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('friends', models.ManyToManyField(related_name='friends_rel_+', to='gamification.FriendProxy')),
                ('user', models.OneToOneField(to=settings.AUTH_USER_MODEL)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='FriendshipRequest',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('recipient', models.ForeignKey(related_name='incoming_requests', to='gamification.FriendProxy')),
                ('sender', models.ForeignKey(related_name='sent_requests', to='gamification.FriendProxy')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.AlterUniqueTogether(
            name='friendshiprequest',
            unique_together=set([('sender', 'recipient')]),
        ),
    ]
