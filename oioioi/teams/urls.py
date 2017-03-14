from django.conf.urls import url

from oioioi.teams import views


contest_patterns = [
    url(r'^team/$', views.team_view, name='team_view'),
    url(r'^teams/$', views.teams_list, name='teams_list'),
    url(r'^team/join/(?P<join_key>[0-9a-zA-Z-_=]+)$', views.join_team_view,
        name='join_team'),
    url(r'^team/delete/$', views.delete_team_view, name='delete_team'),
    url(r'^team/create/$', views.create_team_view, name='create_team'),
    url(r'^team/quit/$', views.quit_team_view, name='quit_team'),
]
