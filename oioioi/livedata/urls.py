from django.urls import path

from oioioi.livedata import views

app_name = 'livedata'

contest_patterns = [
    path(
        'teams/<int:round_id>/',
        views.livedata_teams_view,
        name='livedata_teams_view',
    ),
    path(
        'tasks/<int:round_id>/',
        views.livedata_tasks_view,
        name='livedata_tasks_view',
    ),
    path(
        'events/<int:round_id>/',
        views.livedata_events_view,
        name='livedata_events_view',
    ),
]
