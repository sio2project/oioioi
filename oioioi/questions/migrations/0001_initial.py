# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import oioioi.base.utils.validators
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
            name='Message',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('kind', oioioi.base.fields.EnumField(default=b'QUESTION', max_length=64, verbose_name='kind', choices=[(b'QUESTION', 'Question'), (b'PRIVATE', 'Private message'), (b'PUBLIC', 'Public message')])),
                ('topic', models.CharField(max_length=255, verbose_name='topic', validators=[django.core.validators.MaxLengthValidator(255), oioioi.base.utils.validators.validate_whitespaces])),
                ('content', models.TextField(verbose_name='content')),
                ('date', models.DateTimeField(default=django.utils.timezone.now, verbose_name='date', editable=False)),
                ('author', models.ForeignKey(to=settings.AUTH_USER_MODEL)),
                ('contest', models.ForeignKey(blank=True, to='contests.Contest', null=True)),
                ('problem_instance', models.ForeignKey(blank=True, to='contests.ProblemInstance', null=True)),
                ('round', models.ForeignKey(blank=True, to='contests.Round', null=True)),
                ('top_reference', models.ForeignKey(blank=True, to='questions.Message', null=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='MessageNotifierConfig',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('contest', models.ForeignKey(to='contests.Contest')),
                ('user', models.ForeignKey(verbose_name='username', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'notified about new questions',
                'verbose_name_plural': 'notified about new questions',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='MessageView',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('date', models.DateTimeField(default=django.utils.timezone.now, editable=False)),
                ('message', models.ForeignKey(to='questions.Message')),
                ('user', models.ForeignKey(to=settings.AUTH_USER_MODEL)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='ReplyTemplate',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=255, verbose_name='visible name', blank=True)),
                ('content', models.TextField(verbose_name='content')),
                ('usage_count', models.IntegerField(default=0, verbose_name='usage count')),
                ('contest', models.ForeignKey(blank=True, to='contests.Contest', null=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.AlterUniqueTogether(
            name='messageview',
            unique_together=set([('message', 'user')]),
        ),
        migrations.AlterUniqueTogether(
            name='messagenotifierconfig',
            unique_together=set([('contest', 'user')]),
        ),
    ]
