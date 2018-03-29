# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('programs', '0002_auto_20150218_1346'),
        ('zeus', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='ZeusTestReport',
            fields=[
                ('testreport_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='programs.TestReport')),
                ('nodes', models.IntegerField(null=True)),
                ('check_uid', models.CharField(max_length=255)),
            ],
            options={
            },
            bases=('programs.testreport',),
        ),
        migrations.AddField(
            model_name='zeustestrunprogramsubmission',
            name='nodes',
            field=models.IntegerField(null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='zeustestrunprogramsubmission',
            name='time_limit',
            field=models.IntegerField(null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='zeustestrunreport',
            name='check_uid',
            field=models.CharField(default=0, max_length=255),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='zeustestrunreport',
            name='nodes',
            field=models.IntegerField(null=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='zeusasyncjob',
            name='check_uid',
            field=models.CharField(max_length=255, serialize=False, primary_key=True),
            preserve_default=True,
        ),
    ]
