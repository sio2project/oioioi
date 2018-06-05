# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations


def move_node_data_to_nodelanguageversion(apps, schema_editor):
    Node = apps.get_model('portals', 'Node')
    NodeLanguageVersion = apps.get_model('portals', 'NodeLanguageVersion')

    for node in Node.objects.all():
        node_content = NodeLanguageVersion(node=node,
                                           language=settings.LANGUAGE_CODE,
                                           full_name=node.full_name,
                                           panel_code=node.panel_code)
        node_content.save()


def reverse_node_data_migration(apps, schema_editor):
    Node = apps.get_model('portals', 'Node')
    NodeLanguageVersion = apps.get_model('portals', 'NodeLanguageVersion')

    for node in Node.objects.all():
        try:
            default_node_content = node.language_versions.get(
                language=settings.LANGUAGE_CODE)
        except NodeLanguageVersion.DoesNotExist:
            default_node_content = node.language_versions.first()

        if default_node_content is not None:
            node.full_name = default_node_content.full_name
            node.panel_code = default_node_content.panel_code
            node.save()


class Migration(migrations.Migration):

    dependencies = [
        ('portals', '0006_auto_20180531_1300'),
    ]

    operations = [
        migrations.RunPython(move_node_data_to_nodelanguageversion,
                             reverse_node_data_migration)
    ]
