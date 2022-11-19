# -*- coding: utf-8 -*-

from __future__ import unicode_literals

from django.db import migrations
from django.db.models import Value as V
from django.db.models.functions import Concat, Length, Substr

import oioioi.contests.fields
from oioioi.contests.scores import IntegerScore

def smart_score_copier(apps, schema_editor):
    Contest = apps.get_model('contests', 'Contest')
    ProblemInstance = apps.get_model('contests', 'ProblemInstance')
    Submission = apps.get_model('contests', 'Submission')
    SubmissionReport = apps.get_model('contests', 'SubmissionReport')
    TestReport = apps.get_model('programs', 'TestReport')

    db_alias = schema_editor.connection.alias

    # Firstly, all max_scores will be set as equal to test_max_scores
    # provided that they are not None – this is the behaviour used
    # all contests except for the Algorithmic Engagements
    # and the ACM type contests.

    # This operates on raw, serialized data, which is a bit dirty but works.

    TestReport.objects.using(db_alias).filter(test_max_score__isnull=False) \
        .update(
            max_score=Concat(
                V('int:'),
                Substr(
                    Concat(V('0000000000000000000'), 'test_max_score'),
                    Length(Concat(V('0000000000000000000'), 'test_max_score')) - 18,
                    19
                )
            )
        )

    # Secondly, all max_scores related to the Algorithmic Engagements
    # will be set to either 1 or 0, the same way they are defined
    # in pa_test_scorer from oioioi/pa/utils.py

    pa_test_reports = TestReport.objects.using(db_alias).filter(
        submission_report__submission__problem_instance__contest__controller_name='oioioi.pa.controllers.PAContestController',
        test_max_score__isnull=False)

    pa_test_reports.update(max_score=IntegerScore(1))

    pa_test_reports.filter(test_max_score=0).update(max_score=IntegerScore(0))

    # In the end, all max_scores related to the ACM type contests will be left
    # as none, which agrees with their behaviour defined in the ACM contest
    # controller.

    acm_test_reports = TestReport.objects.using(db_alias).filter(
        submission_report__submission__problem_instance__contest__controller_name='oioioi.acm.controllers.ACMContestController')

    acm_test_reports.update(max_score=None)

def copy_revert(apps, schema_editor):
    TestReport = apps.get_model('programs', 'TestReport')

    db_alias = schema_editor.connection.alias

    TestReport.objects.using(db_alias) \
        .filter(test_max_score__isnull=False) \
        .update(max_score=None)


class Migration(migrations.Migration):

    dependencies = [
        ('programs', '0012_testreport_max_score'),
    ]

    operations = [
        migrations.RunPython(smart_score_copier, copy_revert)
    ]
