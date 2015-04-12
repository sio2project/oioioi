# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import oioioi.base.fields


class Migration(migrations.Migration):

    dependencies = [
        ('contests', '0003_auto_20150218_1309'),
    ]

    operations = [
        migrations.AlterField(
            model_name='probleminstance',
            name='contest',
            field=models.ForeignKey(verbose_name='contest', blank=True, to='contests.Contest', null=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='submission',
            name='kind',
            field=oioioi.base.fields.EnumField(default=b'NORMAL', max_length=64, verbose_name='kind', choices=[(b'NORMAL', 'Normal'), (b'IGNORED', 'Ignored'), (b'SUSPECTED', 'Suspected'), (b'IGNORED_HIDDEN', 'Ignored-Hidden'), (b'USER_OUTS', 'Generate user out'), (b'TESTRUN', 'Test run')]),
            preserve_default=True,
        ),
    ]
