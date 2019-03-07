# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('auth', '0001_initial'),
        ('contests', '0002_auto_20141219_1346'),
    ]

    operations = [
        migrations.CreateModel(
            name='ContestTeacher',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='RegistrationConfig',
            fields=[
                ('contest', models.OneToOneField(primary_key=True, serialize=False, to='contests.Contest')),
                ('is_active_pupil', models.BooleanField(default=True)),
                ('is_active_teacher', models.BooleanField(default=True)),
                ('pupil_key', models.CharField(max_length=40)),
                ('teacher_key', models.CharField(max_length=40)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Teacher',
            fields=[
                ('user', models.OneToOneField(primary_key=True, serialize=False, to=settings.AUTH_USER_MODEL, verbose_name='user')),
                ('is_active', models.BooleanField(default=False, verbose_name='active')),
                ('school', models.CharField(max_length=255, verbose_name='school')),
            ],
            options={
                'permissions': (('teacher', 'Is a teacher'),),
            },
            bases=(models.Model,),
        ),
        migrations.AddField(
            model_name='contestteacher',
            name='contest',
            field=models.ForeignKey(to='contests.Contest', on_delete=models.CASCADE),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='contestteacher',
            name='teacher',
            field=models.ForeignKey(to='teachers.Teacher', on_delete=models.CASCADE),
            preserve_default=True,
        ),
        migrations.AlterUniqueTogether(
            name='contestteacher',
            unique_together=set([('contest', 'teacher')]),
        ),
    ]
