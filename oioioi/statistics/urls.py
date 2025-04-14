from django.urls import re_path

from oioioi.statistics import views

app_name = 'statistics'

contest_patterns = [
    re_path(
        r'^stat/(?P<category>[a-zA-Z]+)/(?P<object_name>[a-z0-9_-]+)$',
        views.statistics_view,
        name='statistics_view',
    ),
    re_path(
        r'^stat/(?P<category>[a-zA-Z]+)$',
        views.statistics_view,
        name='statistics_view_without_object',
    ),
    re_path(r'^stat/$', views.statistics_view, name='statistics_main'),
    re_path(r'^monitoring/$', views.monitoring_view, name='monitoring'),
]
