from django.conf.urls import url

from oioioi.livedata import views

app_name = 'livedata'

contest_patterns = [
    url(r'^teams/(?P<round_id>\d+)/$', views.livedata_teams_view,
        name='livedata_teams_view'),
    url(r'^tasks/(?P<round_id>\d+)/$', views.livedata_tasks_view,
        name='livedata_tasks_view'),
    url(r'^events/(?P<round_id>\d+)/$', views.livedata_events_view,
        name='livedata_events_view'),
]
