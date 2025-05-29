from django.urls import path
from django.urls import re_path

from oioioi.teams import views

app_name = 'teams'

contest_patterns = [
    path('team/', views.team_view, name='team_view'),
    path('teams/', views.teams_list, name='teams_list'),
    re_path(
        r'^team/join/(?P<join_key>[0-9a-zA-Z-_=]+)$',
        views.join_team_view,
        name='join_team',
    ),
    path('team/delete/', views.delete_team_view, name='delete_team'),
    path('team/create/', views.create_team_view, name='create_team'),
    path('team/quit/', views.quit_team_view, name='quit_team'),
]
