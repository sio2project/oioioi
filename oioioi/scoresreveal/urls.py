from django.urls import path

from oioioi.scoresreveal import views

app_name = 'scoresreveal'

contest_patterns = [
    path(
        's/<int:submission_id>/reveal/',
        views.score_reveal_view,
        name='submission_score_reveal',
    ),
]
