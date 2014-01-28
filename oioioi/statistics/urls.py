from django.conf.urls import patterns, url, include

statistics_patterns = patterns('oioioi.statistics.views',
    url(r'^stat/(?P<category>[a-zA-Z]+)/(?P<object_name>[a-z0-9_-]+)$',
        'statistics_view', name='statistics_view'),
    url(r'^stat/(?P<category>[a-zA-Z]+)$', 'statistics_view',
        name='statistics_view_without_object'),
    url(r'^stat/$', 'statistics_view', name='statistics_main'),
)

urlpatterns = patterns('oioioi.statistics.views',
    url(r'^c/(?P<contest_id>[a-z0-9_-]+)/', include(statistics_patterns)),
)

