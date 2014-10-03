from django.conf.urls import patterns, url, include

contest_patterns = patterns('oioioi.teams.views',
    url(r'^team/$', 'team_view', name='team_view'),
    url(r'^teams/$', 'teams_list', name='teams_list'),
    url(r'^team/join/(?P<join_key>[0-9a-zA-Z-_=]+)$', 'join_team_view',
        name='join_team'),
    url(r'^team/delete/$', 'delete_team_view', name='delete_team'),
    url(r'^team/create/$', 'create_team_view', name='create_team'),
    url(r'^team/quit/$', 'quit_team_view', name='quit_team'),
)

urlpatterns = patterns('oioioi.teams.views',
    url(r'^c/(?P<contest_id>[a-z0-9_-]+)/', include(contest_patterns)),
)
