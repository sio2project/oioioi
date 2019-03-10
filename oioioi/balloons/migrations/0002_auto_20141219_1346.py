# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations, models

import oioioi.base.utils.color


class Migration(migrations.Migration):

    dependencies = [
        ('contests', '0001_initial'),
        ('balloons', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='ProblemBalloonsConfig',
            fields=[
                ('problem_instance', models.OneToOneField(related_name='balloons_config', primary_key=True, serialize=False, to='contests.ProblemInstance', verbose_name='problem', on_delete=models.CASCADE)),
                ('color', oioioi.base.utils.color.ColorField(verbose_name='color')),
            ],
            options={
                'verbose_name': 'balloons colors',
                'verbose_name_plural': 'balloons colors',
            },
            bases=(models.Model,),
        ),
        migrations.AddField(
            model_name='balloonsdisplay',
            name='contest',
            field=models.ForeignKey(verbose_name='contest', to='contests.Contest', on_delete=models.CASCADE),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='balloonsdisplay',
            name='user',
            field=models.ForeignKey(verbose_name='user', to=settings.AUTH_USER_MODEL, on_delete=models.CASCADE),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='balloonsdeliveryaccessdata',
            name='contest',
            field=models.OneToOneField(verbose_name='contest', to='contests.Contest', on_delete=models.CASCADE),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='balloondelivery',
            name='problem_instance',
            field=models.ForeignKey(verbose_name='problem', to='contests.ProblemInstance', on_delete=models.CASCADE),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='balloondelivery',
            name='user',
            field=models.ForeignKey(verbose_name='user', to=settings.AUTH_USER_MODEL, on_delete=models.CASCADE),
            preserve_default=True,
        ),
        migrations.AlterUniqueTogether(
            name='balloondelivery',
            unique_together=set([('user', 'problem_instance')]),
        ),
    ]
