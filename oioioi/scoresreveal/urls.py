from django.conf.urls import url

from oioioi.scoresreveal import views

contest_patterns = [
    url(r'^s/(?P<submission_id>\d+)/reveal/$', views.score_reveal_view,
        name='submission_score_reveal'),
]
