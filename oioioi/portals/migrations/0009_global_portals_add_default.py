# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations
from django.conf import settings
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
        root = Node.objects.create(short_name='',
                                   parent=None,
                                   **{'lft': 0, 'rght': 0, 'level': 0,
                                      'tree_id': 0})
        NodeLanguageVersion = apps.get_model('portals', 'NodeLanguageVersion')
        name = render_to_string('portals/portal-initial-main-page-name.txt')
        body = render_to_string('portals/portal-initial-main-page-body.txt')
        NodeLanguageVersion.objects.create(node=root,
                                           language=settings.LANGUAGE_CODE,
                                           full_name=name,
                                           panel_code=body)
        # MPTT will be rebuild after migration (see handlers)
        Portal.objects.create(owner=None,
                              root=root,
                              short_description=_("Default global portal"),
                              link_name='default',
                              is_public=True)


class Migration(migrations.Migration):
    dependencies = [
        ('portals', '0008_auto_20180531_1311'),
    ]

    operations = [
        migrations.RunPython(create_default_global_portal),
    ]
