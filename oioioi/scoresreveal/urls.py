from django.urls import re_path

from oioioi.scoresreveal import views

app_name = 'scoresreveal'

contest_patterns = [
    re_path(
        r'^s/(?P<submission_id>\d+)/reveal/$',
        views.score_reveal_view,
        name='submission_score_reveal',
    ),
]
