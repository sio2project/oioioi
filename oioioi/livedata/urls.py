from django.conf.urls import patterns, include, url

livedata_patterns = patterns('oioioi.livedata.views',
    url(r'^teams/(?P<round_id>\d+)/$', 'livedata_teams_view',
        name='livedata_teams_view'),
    url(r'^tasks/(?P<round_id>\d+)/$', 'livedata_tasks_view',
        name='livedata_tasks_view'),
    url(r'^events/(?P<round_id>\d+)/$', 'livedata_events_view',
        name='livedata_events_view'),
)

urlpatterns = patterns('oioioi.livedata.views',
    url(r'^c/(?P<contest_id>[a-z0-9_-]+)/livedata/',
        include(livedata_patterns)),
)
