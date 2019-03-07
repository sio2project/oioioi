# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import datetime

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('contests', '0005_auto_20150531_2248'),
    ]

    operations = [
        migrations.CreateModel(
            name='Ranking',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('key', models.CharField(max_length=255)),
                ('needs_recalculation', models.BooleanField(default=True)),
                ('serialized_data', models.BinaryField(null=True)),
                ('invalidation_date', models.DateTimeField(auto_now_add=True)),
                ('last_recalculation_date', models.DateTimeField(null=True)),
                ('last_recalculation_duration', models.DurationField(default=datetime.timedelta(0))),
                ('cooldown_date', models.DateTimeField(auto_now_add=True)),
                ('contest', models.ForeignKey(to='contests.Contest', on_delete=models.CASCADE)),
            ],
        ),
        migrations.CreateModel(
            name='RankingPage',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('nr', models.IntegerField()),
                ('data', models.TextField()),
                ('ranking', models.ForeignKey(related_name='pages', to='rankings.Ranking', on_delete=models.CASCADE)),
            ],
        ),
        migrations.CreateModel(
            name='RankingRecalc',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
            ],
        ),
        migrations.AddField(
            model_name='ranking',
            name='recalc_in_progress',
            field=models.ForeignKey(to='rankings.RankingRecalc', null=True, on_delete=models.CASCADE),
        ),
    ]
