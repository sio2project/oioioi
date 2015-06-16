# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations

from oioioi.base.utils import generate_key


def set_default_values(apps, schema_editor):
    """For every :class:`oioioi.problems.models.Problem`.main_problem_instance
       replaces it with copy with contest and round set on None.
       This function assumes that each :class:`oioioi.problems.models.Problem`
       has main_problem_instance.

       Also if there is no ProblemSite for given Problem creates one.

       Field author is set as creator of the problem's problem_package
       (function assumes that there is only one problem_package for problem)
    """
    Problem = apps.get_model('problems', 'Problem')
    ProblemSite = apps.get_model('problems', 'ProblemSite')

    for problem in Problem.objects.all():
        pi = problem.main_problem_instance
        if pi.contest:
            pi.id = pi.pk = None # there will be a copy created when 'save()'
            pi.contest = pi.round = None
            pi.save()
            for test in problem.main_problem_instance.test_set.all():
                test.id = test.pk = None
                test.problem_instance = pi
                test.save()
            problem.main_problem_instance = pi
            problem.save()

        if not ProblemSite.objects.filter(problem=problem).exists():
            site = ProblemSite(problem=problem, url_key=generate_key())
            site.save()

        if not problem.author:
            problem.author = problem.problempackage_set.get().created_by
            problem.save()


class Migration(migrations.Migration):

    dependencies = [
        ('problems', '0003_problemsite'),
        ('problems', '0004_problem_main_problem_instance'),
        ('problems', '0005_add_tags'),
        ('contests', '0005_auto_20150531_2248'),
        ('programs', '0003_auto_20150420_2002'),
    ]

    operations = [
        migrations.RunPython(set_default_values),
    ]
