from django.conf.urls import url

from oioioi.statistics import views

app_name = 'statistics'

contest_patterns = [
    url(
        r'^stat/(?P<category>[a-zA-Z]+)/(?P<object_name>[a-z0-9_-]+)$',
        views.statistics_view,
        name='statistics_view',
    ),
    url(
        r'^stat/(?P<category>[a-zA-Z]+)$',
        views.statistics_view,
        name='statistics_view_without_object',
    ),
    url(r'^stat/$', views.statistics_view, name='statistics_main'),
]
