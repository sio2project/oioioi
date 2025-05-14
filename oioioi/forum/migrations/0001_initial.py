# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('contests', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Category',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=255, verbose_name='category')),
            ],
            options={
                'verbose_name': 'category',
                'verbose_name_plural': 'categories',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Forum',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('visible', models.BooleanField(default=True, verbose_name='forum is visible after lock')),
                ('lock_date', models.DateTimeField(null=True, verbose_name='autolock date', blank=True)),
                ('unlock_date', models.DateTimeField(null=True, verbose_name='autounlock date', blank=True)),
                ('contest', models.OneToOneField(to='contests.Contest', on_delete=models.CASCADE)),
            ],
            options={
                'verbose_name': 'forum',
                'verbose_name_plural': 'forums',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Post',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('content', models.TextField(verbose_name='post')),
                ('add_date', models.DateTimeField(default=django.utils.timezone.now, verbose_name='add date', blank=True)),
                ('last_edit_date', models.DateTimeField(null=True, verbose_name='last edit', blank=True)),
                ('reported', models.BooleanField(default=False, verbose_name='reported')),
                ('hidden', models.BooleanField(default=False, verbose_name='hidden')),
                ('author', models.ForeignKey(verbose_name='author', to=settings.AUTH_USER_MODEL, on_delete=models.CASCADE)),
            ],
            options={
                'ordering': ('add_date',),
                'verbose_name': 'post',
                'verbose_name_plural': 'posts',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Thread',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=255, verbose_name='thread')),
                ('category', models.ForeignKey(verbose_name='category', to='forum.Category', on_delete=models.CASCADE)),
                ('last_post', models.ForeignKey(related_name='last_post_of', on_delete=django.db.models.deletion.SET_NULL, verbose_name='last post', to='forum.Post', null=True)),
            ],
            options={
                'ordering': ('-last_post__id',),
                'verbose_name': 'thread',
                'verbose_name_plural': 'threads',
            },
            bases=(models.Model,),
        ),
        migrations.AddField(
            model_name='post',
            name='thread',
            field=models.ForeignKey(verbose_name='thread', to='forum.Thread', on_delete=models.CASCADE),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='category',
            name='forum',
            field=models.ForeignKey(verbose_name='forum', to='forum.Forum', on_delete=models.CASCADE),
            preserve_default=True,
        ),
    ]
