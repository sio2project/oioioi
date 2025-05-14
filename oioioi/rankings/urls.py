from django.urls import path
from django.urls import re_path

from oioioi.rankings import views

app_name = 'rankings'

contest_patterns = [
    path('ranking/', views.ranking_view, name='default_ranking'),
    path(
        'ranking/edit_message/',
        views.edit_ranking_message_view,
        name='edit_ranking_message',
    ),
    path(
        'ranking/get_users_in_ranking/',
        views.get_users_in_ranking_view,
        name='get_users_in_ranking',
    ),
    re_path(r'^ranking/(?P<key>[a-z0-9_-]+)/$', views.ranking_view, name='ranking'),
    re_path(
        r'^ranking/(?P<key>[a-z0-9_-]+)/csv/$',
        views.ranking_csv_view,
        name='ranking_csv',
    ),
    re_path(
        r'^ranking/(?P<key>[a-z0-9_-]+)/invalidate/$',
        views.ranking_invalidate_view,
        name='ranking_invalidate',
    ),
]
