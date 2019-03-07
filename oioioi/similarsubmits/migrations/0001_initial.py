# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('contests', '0003_auto_20150218_1309'),
    ]

    operations = [
        migrations.CreateModel(
            name='SubmissionsSimilarityEntry',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('guilty', models.BooleanField(default=True, verbose_name='guilty')),
            ],
            options={
                'verbose_name': 'submissions similarity entry',
                'verbose_name_plural': 'submissions similarity entries',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='SubmissionsSimilarityGroup',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('comment', models.TextField(verbose_name='admin comment', blank=True)),
                ('contest', models.ForeignKey(verbose_name='contest', to='contests.Contest', on_delete=models.CASCADE)),
            ],
            options={
                'verbose_name': 'submissions similarity',
                'verbose_name_plural': 'submissions similarities',
            },
            bases=(models.Model,),
        ),
        migrations.AddField(
            model_name='submissionssimilarityentry',
            name='group',
            field=models.ForeignKey(related_name='submissions', verbose_name='group', to='similarsubmits.SubmissionsSimilarityGroup', on_delete=models.CASCADE),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='submissionssimilarityentry',
            name='submission',
            field=models.ForeignKey(related_name='similarities', verbose_name='submission', to='contests.Submission', on_delete=models.CASCADE),
            preserve_default=True,
        ),
        migrations.AlterUniqueTogether(
            name='submissionssimilarityentry',
            unique_together=set([('submission', 'group')]),
        ),
    ]
