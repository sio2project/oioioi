# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.utils.timezone
import oioioi.contestlogo.models
import oioioi.filetracker.fields


class Migration(migrations.Migration):

    dependencies = [
        ('contests', '0001_initial'),
        ('contestlogo', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='ContestLogo',
            fields=[
                ('contest', models.OneToOneField(primary_key=True, serialize=False, to='contests.Contest', verbose_name='contest')),
                ('image', oioioi.filetracker.fields.FileField(upload_to=oioioi.contestlogo.models.make_logo_filename, verbose_name='logo image')),
                ('updated_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('link', models.URLField(null=True, verbose_name='external contest webpage url', blank=True)),
            ],
            options={
                'verbose_name': 'contest logo',
                'verbose_name_plural': 'contest logo',
            },
            bases=(models.Model,),
        ),
        migrations.AddField(
            model_name='contesticon',
            name='contest',
            field=models.ForeignKey(verbose_name='contest', to='contests.Contest'),
            preserve_default=True,
        ),
    ]
