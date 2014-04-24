from django.conf.urls import patterns, include, url

contest_patterns = patterns('oioioi.ctimes.views',
    url(r'^ctimes/$', 'ctimes_view', name='ctimes')
)

urlpatterns = patterns('oioioi.ctimes.views',
    url(r'^c/(?P<contest_id>[a-z0-9_-]+)/', include(contest_patterns)),
    url(r'^ctimes/$', 'ctimes_view', name='ctimes2')
)
