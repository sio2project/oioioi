from django.urls import re_path

from oioioi.teams import views

app_name = 'teams'

contest_patterns = [
    re_path(r'^team/$', views.team_view, name='team_view'),
    re_path(r'^teams/$', views.teams_list, name='teams_list'),
    re_path(
        r'^team/join/(?P<join_key>[0-9a-zA-Z-_=]+)$',
        views.join_team_view,
        name='join_team',
    ),
    re_path(r'^team/delete/$', views.delete_team_view, name='delete_team'),
    re_path(r'^team/create/$', views.create_team_view, name='create_team'),
    re_path(r'^team/quit/$', views.quit_team_view, name='quit_team'),
]
