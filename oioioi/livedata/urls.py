from django.urls import re_path

from oioioi.livedata import views

app_name = 'livedata'

contest_patterns = [
    re_path(
        r'^teams/(?P<round_id>\d+)/$',
        views.livedata_teams_view,
        name='livedata_teams_view',
    ),
    re_path(
        r'^tasks/(?P<round_id>\d+)/$',
        views.livedata_tasks_view,
        name='livedata_tasks_view',
    ),
    re_path(
        r'^events/(?P<round_id>\d+)/$',
        views.livedata_events_view,
        name='livedata_events_view',
    ),
]
