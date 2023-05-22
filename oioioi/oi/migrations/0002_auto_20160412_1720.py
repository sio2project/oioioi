# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('oi', '0001_initial'),
    ]

    database_operations = [
        migrations.AlterField(
            model_name='oionsiteregistration',
            name='region',
            field=models.IntegerField(verbose_name='region', null=True),
        ),
    ]

    state_operations = [
        migrations.DeleteModel('oionsiteregistration'),
        migrations.DeleteModel('region'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=database_operations,
            state_operations=state_operations)
    ]
