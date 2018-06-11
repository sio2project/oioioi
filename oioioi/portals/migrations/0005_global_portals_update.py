# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import django.core.validators
from django.db import migrations, models
import re

from django.template.loader import render_to_string
from django.utils.translation import ugettext_lazy as _


def create_default_global_portal(apps, schema_editor):
    Portal = apps.get_model('portals', 'Portal')
    try:
        global_portal = Portal.objects.get(owner=None)
        global_portal.short_description = _("Default global portal")
        global_portal.link_name = 'default'
        global_portal.is_public = True
        global_portal.save()
    except Portal.DoesNotExist:
        Node = apps.get_model('portals', 'Node')
        name = render_to_string(
            'portals/global-portal-initial-main-page-name.txt')
        body = render_to_string(
            'portals/global-portal-initial-main-page-body.txt')
        root = Node.objects.create(full_name=name, short_name='',
                                   parent=None, panel_code=body,
                                   **{'lft': 0, 'rght': 0, 'level': 0,
                                      'tree_id': 0})
        # MPTT will be rebuild after migration (see handlers)
        Portal.objects.create(owner=None,
                              root=root,
                              short_description=_("Default global portal"),
                              link_name='default',
                              is_public=True)


class Migration(migrations.Migration):
    dependencies = [
        ('portals', '0004_auto_20170523_0848'),
    ]

    operations = [
        migrations.AddField(
            model_name='portal',
            name='link_name',
            field=models.CharField(help_text='Shown in the URL.', max_length=40,
                                   null=True, unique=True,
                                   validators=[
                                       django.core.validators.RegexValidator(
                                           re.compile(b'^[a-z0-9_-]+$'),
                                           "Enter a valid 'slug' consisting of "
                                           "lowercase letters, numbers, "
                                           "underscores or hyphens.",
                                           b'invalid')]),
        ),
        migrations.AddField(
            model_name='portal',
            name='is_public',
            field=models.BooleanField(default=False, verbose_name='is public'),
        ),
        migrations.AddField(
            model_name='portal',
            name='short_description',
            field=models.CharField(default='My portal.', max_length=256,
                                   null=True, verbose_name='short description'),
        ),
        migrations.RunPython(create_default_global_portal),
    ]
