# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import oioioi.prizes.models
import oioioi.filetracker.fields
import django.utils.timezone
from django.conf import settings
import oioioi.base.fields
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
        ('contests', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Prize',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=100, verbose_name='name')),
                ('quantity', models.IntegerField(default=1, verbose_name='quantity', validators=[django.core.validators.MinValueValidator(1)])),
                ('order', models.IntegerField(verbose_name='position in non-strict distribution order', validators=[django.core.validators.MinValueValidator(1)])),
                ('contest', models.ForeignKey(to='contests.Contest')),
            ],
            options={
                'ordering': ['prize_giving', 'order', 'id'],
                'verbose_name': 'prize',
                'verbose_name_plural': 'prizes',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='PrizeForUser',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('prize', models.ForeignKey(to='prizes.Prize')),
                ('user', models.ForeignKey(to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['prize', 'user'],
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='PrizeGiving',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('date', models.DateTimeField(help_text="Leave blank for 'later'.", null=True, verbose_name='Distribution date', blank=True)),
                ('name', models.CharField(help_text='Prize-givings with the same name are listed together.', max_length=100, verbose_name='name')),
                ('key', models.CharField(max_length=100, verbose_name='awarding rules', choices=[(b'', b'')])),
                ('state', oioioi.base.fields.EnumField(default=b'NOT_SCHEDULED', max_length=64, editable=False, choices=[(b'NOT_SCHEDULED', 'NOT SCHEDULED'), (b'SCHEDULED', 'SCHEDULED'), (b'FAILURE', 'FAILURE'), (b'SUCCESS', 'SUCCESS')])),
                ('report', oioioi.filetracker.fields.FileField(upload_to=oioioi.prizes.models._make_report_filename, null=True, editable=False)),
                ('version', models.DateTimeField(default=django.utils.timezone.now, editable=False)),
                ('contest', models.ForeignKey(to='contests.Contest')),
            ],
            options={
                'ordering': ['-date', 'id'],
                'verbose_name': 'prize-giving',
                'verbose_name_plural': 'prize-givings',
            },
            bases=(models.Model,),
        ),
        migrations.AddField(
            model_name='prize',
            name='prize_giving',
            field=models.ForeignKey(verbose_name='prize-giving', to='prizes.PrizeGiving'),
            preserve_default=True,
        ),
    ]
