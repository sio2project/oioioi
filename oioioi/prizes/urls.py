from django.conf.urls import patterns, include, url


contest_patterns = patterns('oioioi.prizes.views',
    url(r'^prizes/$', 'prizes_view', name='default_prizes'),
    url(r'^prizes/(?P<key>\d+)/$', 'prizes_view', name='prizes'),
    url(r'^prizes/download_report/(?P<pg_id>\d+)/$', 'download_report_view'),
)

urlpatterns = patterns('oioioi.prizes.views',
    url(r'^c/(?P<contest_id>[a-z0-9_-]+)/', include(contest_patterns)),
)
