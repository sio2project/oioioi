# -*- coding: utf-8 -*-
# Populating models created in '0008_compilers_part1'
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations


def set_default_compilers(apps, schema_editor):
    Problem = apps.get_model('problems', 'Problem')
    ProblemCompiler = apps.get_model('programs', 'ProblemCompiler')
    db_alias = schema_editor.connection.alias

    for problem in Problem.objects.all():
        for language in getattr(settings, 'SUBMITTABLE_EXTENSIONS', {}):
            compiler = settings.DEFAULT_COMPILERS[language]
            ProblemCompiler.objects.using(db_alias).create(problem=problem, language=language,
                                                           compiler=compiler)


class Migration(migrations.Migration):

    dependencies = [
        ('programs', '0008_compilers_part1'),
    ]

    operations = [
        migrations.RunPython(set_default_compilers, migrations.RunPython.noop),
    ]
