# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('contests', '0001_initial'),
        ('problems', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='probleminstance',
            name='problem',
            field=models.ForeignKey(verbose_name='problem', to='problems.Problem', on_delete=models.CASCADE),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='probleminstance',
            name='round',
            field=models.ForeignKey(verbose_name='round', blank=True, to='contests.Round', null=True, on_delete=models.CASCADE),
            preserve_default=True,
        ),
        migrations.AlterUniqueTogether(
            name='probleminstance',
            unique_together=set([('contest', 'short_name')]),
        ),
        migrations.AddField(
            model_name='failurereport',
            name='submission_report',
            field=models.ForeignKey(to='contests.SubmissionReport', on_delete=models.CASCADE),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='contestview',
            name='contest',
            field=models.ForeignKey(to='contests.Contest', on_delete=models.CASCADE),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='contestview',
            name='user',
            field=models.ForeignKey(to=settings.AUTH_USER_MODEL, on_delete=models.CASCADE),
            preserve_default=True,
        ),
        migrations.AlterUniqueTogether(
            name='contestview',
            unique_together=set([('user', 'contest')]),
        ),
        migrations.AddField(
            model_name='contestpermission',
            name='contest',
            field=models.ForeignKey(to='contests.Contest', on_delete=models.CASCADE),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='contestpermission',
            name='user',
            field=models.ForeignKey(to=settings.AUTH_USER_MODEL, on_delete=models.CASCADE),
            preserve_default=True,
        ),
        migrations.AlterUniqueTogether(
            name='contestpermission',
            unique_together=set([('user', 'contest', 'permission')]),
        ),
        migrations.AddField(
            model_name='contestlink',
            name='contest',
            field=models.ForeignKey(verbose_name='contest', to='contests.Contest', on_delete=models.CASCADE),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='contestattachment',
            name='contest',
            field=models.ForeignKey(related_name='c_attachments', verbose_name='contest', to='contests.Contest', on_delete=models.CASCADE),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='contestattachment',
            name='round',
            field=models.ForeignKey(related_name='r_attachments', verbose_name='round', blank=True, to='contests.Round', null=True, on_delete=models.CASCADE),
            preserve_default=True,
        ),
    ]
