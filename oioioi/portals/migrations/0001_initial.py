# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import oioioi.base.utils.validators
import re
import mptt.fields
from django.conf import settings
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Node',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('full_name', models.CharField(help_text='Shown in the navigation menu.', max_length=32, verbose_name='full name', validators=[oioioi.base.utils.validators.validate_whitespaces])),
                ('short_name', models.CharField(help_text='Shown in the URL.', max_length=32, verbose_name='short name', validators=[django.core.validators.RegexValidator(re.compile(b'^[a-z0-9_-]+$'), "Enter a valid 'slug' consisting of lowercase letters, numbers, underscores or hyphens.", b'invalid')])),
                ('panel_code', models.TextField(verbose_name='panel code', blank=True)),
                ('lft', models.PositiveIntegerField(editable=False, db_index=True)),
                ('rght', models.PositiveIntegerField(editable=False, db_index=True)),
                ('tree_id', models.PositiveIntegerField(editable=False, db_index=True)),
                ('level', models.PositiveIntegerField(editable=False, db_index=True)),
                ('parent', mptt.fields.TreeForeignKey(related_name='children', verbose_name='parent', to='portals.Node', null=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Portal',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('owner', models.OneToOneField(null=True, to=settings.AUTH_USER_MODEL)),
                ('root', models.OneToOneField(to='portals.Node')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.AlterUniqueTogether(
            name='node',
            unique_together=set([('parent', 'short_name')]),
        ),
    ]
