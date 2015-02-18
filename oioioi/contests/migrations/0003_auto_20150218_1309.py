# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from functools import partial

from django.db import models, migrations

from oioioi.contests.scores import ScoreValue

def _sum_scores(scores):
    scores = [s for s in scores if s is not None]
    return scores and sum(scores[1:], scores[0]) or None

def recompute_user_results_for_contest(round_filter, apps, _schema_editor):
    UserResultForContest = apps.get_model('contests', 'UserResultForContest')
    UserResultForRound = apps.get_model('contests', 'UserResultForRound')

    for result in UserResultForContest.objects.all():
        scores = UserResultForRound.objects \
                .filter(user=result.user) \
                .filter(round__contest=result.contest) \
                .values_list('score', flat=True)
        scores = round_filter(scores)
        result.score = _sum_scores(map(ScoreValue.deserialize, scores))
        result.save()

def new_filter(qs):
    return qs.filter(round__is_trial=False)

def old_filter(qs):
    return qs


class Migration(migrations.Migration):

    dependencies = [
        ('contests', '0002_auto_20141219_1346'),
    ]

    operations = [
        migrations.RunPython(
            partial(recompute_user_results_for_contest, new_filter),
            partial(recompute_user_results_for_contest, old_filter),
        ),
    ]
