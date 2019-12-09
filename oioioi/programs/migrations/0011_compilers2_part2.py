# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations


def delete_invalid_compilers(apps, schema_editor):
    ProblemCompiler = apps.get_model('programs', 'ProblemCompiler')
    AVAILABLE_COMPILERS = getattr(settings, 'AVAILABLE_COMPILERS', {})

    for problem_compiler in ProblemCompiler.objects.all():
        language = problem_compiler.language
        compilers_for_language = AVAILABLE_COMPILERS.get(language, {})
        if problem_compiler.compiler not in compilers_for_language:
            default_compiler = settings.DEFAULT_COMPILERS[language]
            problem_compiler.compiler = default_compiler
            problem_compiler.auto_created = True
            problem_compiler.save()


class Migration(migrations.Migration):

    dependencies = [
        ('programs', '0010_compilers2_part1'),
    ]

    operations = [
        migrations.RunPython(delete_invalid_compilers, migrations.RunPython.noop),
    ]
