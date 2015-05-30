# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import oioioi.base.fields


class Migration(migrations.Migration):

    dependencies = [
        ('contests', '0004_auto_20150420_2002'),
    ]

    operations = [
        migrations.AddField(
            model_name='probleminstance',
            name='needs_rejudge',
            field=models.BooleanField(default=False, verbose_name=b'needs rejudge'),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='scorereport',
            name='status',
            field=oioioi.base.fields.EnumField(blank=True, max_length=64, null=True, choices=[(b'?', 'Pending'), (b'OK', 'OK'), (b'ERR', 'Error'), (b'CE', 'Compilation failed'), (b'RE', 'Runtime error'), (b'WA', 'Wrong answer'), (b'TLE', 'Time limit exceeded'), (b'MLE', 'Memory limit exceeded'), (b'OLE', 'Output limit exceeded'), (b'SE', 'System error'), (b'RV', 'Rule violation'), (b'INI_OK', 'Initial tests: OK'), (b'INI_ERR', 'Initial tests: failed')]),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='submission',
            name='kind',
            field=oioioi.base.fields.EnumField(default=b'NORMAL', max_length=64, verbose_name='kind', choices=[(b'NORMAL', 'Normal'), (b'IGNORED', 'Ignored'), (b'SUSPECTED', 'Suspected'), (b'IGNORED_HIDDEN', 'Ignored-Hidden'), (b'USER_OUTS', 'Generate user out')]),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='submission',
            name='status',
            field=oioioi.base.fields.EnumField(default=b'?', max_length=64, verbose_name='status', choices=[(b'?', 'Pending'), (b'OK', 'OK'), (b'ERR', 'Error'), (b'CE', 'Compilation failed'), (b'RE', 'Runtime error'), (b'WA', 'Wrong answer'), (b'TLE', 'Time limit exceeded'), (b'MLE', 'Memory limit exceeded'), (b'OLE', 'Output limit exceeded'), (b'SE', 'System error'), (b'RV', 'Rule violation'), (b'INI_OK', 'Initial tests: OK'), (b'INI_ERR', 'Initial tests: failed')]),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='submissionreport',
            name='kind',
            field=oioioi.base.fields.EnumField(default=b'FINAL', max_length=64, choices=[(b'FINAL', 'Final report'), (b'FAILURE', 'Evaluation failure report'), (b'INITIAL', 'Initial report'), (b'NORMAL', 'Normal report'), (b'FULL', 'Full report'), (b'HIDDEN', 'Hidden report (for admins only)'), (b'USER_OUTS', 'Report with user out')]),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='userresultforproblem',
            name='status',
            field=oioioi.base.fields.EnumField(blank=True, max_length=64, null=True, choices=[(b'?', 'Pending'), (b'OK', 'OK'), (b'ERR', 'Error'), (b'CE', 'Compilation failed'), (b'RE', 'Runtime error'), (b'WA', 'Wrong answer'), (b'TLE', 'Time limit exceeded'), (b'MLE', 'Memory limit exceeded'), (b'OLE', 'Output limit exceeded'), (b'SE', 'System error'), (b'RV', 'Rule violation'), (b'INI_OK', 'Initial tests: OK'), (b'INI_ERR', 'Initial tests: failed')]),
            preserve_default=True,
        ),
    ]
