# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('contests', '0006_contestattachment_pub_date'),
    ]

    operations = [
        migrations.AlterField(
            model_name='contest',
            name='contact_email',
            field=models.EmailField(help_text='Address of contest owners. Sent emails related to this contest (i.e. submission confirmations) will have the return address set to this value. Defaults to system admins address if left empty.', max_length=254, verbose_name='contact email', blank=True),
        ),
        migrations.AlterField(
            model_name='probleminstance',
            name='submissions_limit',
            field=models.IntegerField(default=10, verbose_name='submissions limit'),
        ),
    ]
