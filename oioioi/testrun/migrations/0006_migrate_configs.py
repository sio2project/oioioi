# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
from django.db.models import Subquery, OuterRef

def add_probleminstance_test_run_configs(apps, schema_editor):
    """ Copy all existing problem configs as probleminstance configs.

        If a problem instance config already exists, modify it only.
        If not, create a new one.
    """
    # We get the model from the versioned app registry;
    # if we directly import it, it'll be the wrong version
    ProblemInstance = apps.get_model('contests', 'ProblemInstance')
    TestRunConfigForInstance = apps.get_model('testrun', 'TestRunConfigForInstance')
    TestRunConfig = apps.get_model('testrun', 'TestRunConfig')
    db_alias = schema_editor.connection.alias

    # First, create configs for those instances that should have it.
    # We won't bother setting the limits now as they will have to be updated anyway.
    instances = ProblemInstance.objects.using(db_alias).all() \
        .filter(test_run_config__isnull=True, problem__test_run_config__isnull=False)

    new_configs = []
    BULK_LIMIT = 200
    for pi in instances:
        new_configs.append(TestRunConfigForInstance(problem_instance = pi))
        if len(new_configs) >= BULK_LIMIT:
            TestRunConfigForInstance.objects.using(db_alias).bulk_create(new_configs)
            new_configs = []

    TestRunConfigForInstance.objects.using(db_alias).bulk_create(new_configs)

    # Now, update all instance configs so that each will have the right limits set.
    # This only works since Django 1.11
    TestRunConfigForInstance.objects.using(db_alias).all().update(
        memory_limit=Subquery(
            TestRunConfigForInstance.objects.filter(pk=OuterRef('pk')) \
                .values('problem_instance__problem__test_run_config__memory_limit')[:1]),
        time_limit=Subquery(
            TestRunConfigForInstance.objects.filter(pk=OuterRef('pk')) \
                .values('problem_instance__problem__test_run_config__time_limit')[:1]),
    )

    TestRunConfig.objects.using(db_alias).all().delete()

def delete_probleminstance_test_run_configs(apps, schema_editor):
    """ Config for each problem will be based on its main instance's config
        as this is likely the one that hasn't been changed since the migration.

        All time and memory limits set after the migration will be therefore
        deleted.

        That's why this function (and the reverting possibility) exists
        mostly for testing purposes.

        Use with caution.
    """
    # We get the model from the versioned app registry;
    # if we directly import it, it'll be the wrong version
    Problem = apps.get_model('problems', 'Problem')
    TestRunConfig = apps.get_model('testrun', 'TestRunConfig')
    TestRunConfigForInstance = apps.get_model('testrun', 'TestRunConfigForInstance')
    db_alias = schema_editor.connection.alias

    problems = Problem.objects.using(db_alias) \
        .filter(main_problem_instance__test_run_config__isnull=False) \
        .select_related('main_problem_instance__test_run_config')
    new_configs = []
    BULK_LIMIT = 200

    for problem in problems:
        old_config = problem.main_problem_instance.test_run_config
        new_configs.append(TestRunConfig(
            problem=problem,
            time_limit=old_config.time_limit,
            memory_limit=old_config.memory_limit))

        if len(new_configs) >= BULK_LIMIT:
            TestRunConfig.objects.using(db_alias).bulk_create(new_configs)
            new_configs = []

    TestRunConfig.objects.using(db_alias).bulk_create(new_configs)

    # Remove time and memory limit information from problem instance configs.
    # Do not remove the configs themselves. Let them be.
    TestRunConfigForInstance.objects.using(db_alias).all() \
        .update(time_limit=None, memory_limit=None)

class Migration(migrations.Migration):

    dependencies = [
        ('testrun', '0005_auto_20200524_2227'),
    ]

    operations = [
        migrations.RunPython(add_probleminstance_test_run_configs, delete_probleminstance_test_run_configs)
    ]
