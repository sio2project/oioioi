# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations

def change_execution_mode(apps, schema_editor):
    ProgramsConfig = apps.get_model('programs', 'ProgramsConfig')

    db_alias = schema_editor.connection.alias

    ProgramsConfig.objects.using(db_alias).filter(execuction_mode='vcpu') \
        .update(execuction_mode='sio2jail')


class Migration(migrations.Migration):

    dependencies = [
        ('programs', '0014_remove_testreport_test_max_score'),
    ]

    operations = [
        migrations.RunPython(change_execution_mode, reverse_code=migrations.RunPython.noop),
    ]
