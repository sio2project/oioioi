# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion

def add_probleminstance_score_reveal_configs(apps, schema_editor):
    """ Copy all existing problem configs as probleminstance configs.
    """
    # We get the model from the versioned app registry;
    # if we directly import it, it'll be the wrong version
    ProblemInstance = apps.get_model('contests', 'ProblemInstance')
    ScoreRevealConfig = apps.get_model('scoresreveal', 'ScoreRevealConfig')
    db_alias = schema_editor.connection.alias

    instances = ProblemInstance.objects.using(db_alias) \
        .filter(problem__scores_reveal_config__isnull=False) \
        .select_related('problem__scores_reveal_config')
    new_configs = []
    BULK_LIMIT = 200

    for pi in instances:
        old_config = pi.problem.scores_reveal_config
        new_configs.append(ScoreRevealConfig(
            problem=None, problem_instance = pi,
            reveal_limit=old_config.reveal_limit,
            disable_time=old_config.disable_time))

        if len(new_configs) >= BULK_LIMIT:
            ScoreRevealConfig.objects.using(db_alias).bulk_create(new_configs)
            new_configs = []

    ScoreRevealConfig.objects.using(db_alias).bulk_create(new_configs)
    ScoreRevealConfig.objects.using(db_alias).filter(problem_instance__isnull=True).delete()

def delete_probleminstance_score_reveal_configs(apps, schema_editor):
    """ Config for each problem will be based on its main instance's config.
        Configs of non-main instances will be lost.

        As main instances can't be configured manually, basically all configs
        changed or added after the migration will be lost.
        This function is probably only useful for testing purposes
        (and for the purpose of this migration being reversible at all).

        Use carefully.
    """
    # We get the model from the versioned app registry;
    # if we directly import it, it'll be the wrong version
    Problem = apps.get_model('problems', 'Problem')
    ScoreRevealConfig = apps.get_model('scoresreveal', 'ScoreRevealConfig')
    db_alias = schema_editor.connection.alias

    problems = Problem.objects.using(db_alias) \
        .filter(main_problem_instance__scores_reveal_config__isnull=False) \
        .select_related('main_problem_instance__scores_reveal_config')
    new_configs = []
    BULK_LIMIT = 200

    for problem in problems:
        old_config = problem.main_problem_instance.scores_reveal_config
        new_configs.append(ScoreRevealConfig(
            problem=problem, problem_instance = None,
            reveal_limit=old_config.reveal_limit,
            disable_time=old_config.disable_time))

        if len(new_configs) >= BULK_LIMIT:
            ScoreRevealConfig.objects.using(db_alias).bulk_create(new_configs)
            new_configs = []

    ScoreRevealConfig.objects.using(db_alias).bulk_create(new_configs)
    ScoreRevealConfig.objects.using(db_alias).filter(problem__isnull=True).delete()

class Migration(migrations.Migration):

    dependencies = [
        ('contests', '0012_auto_20200128_1451'),
        ('scoresreveal', '0002_auto_20200523_1323'),
    ]

    operations = [
        migrations.RunPython(add_probleminstance_score_reveal_configs, delete_probleminstance_score_reveal_configs)
    ]
