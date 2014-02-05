from django.conf.urls import patterns, include, url

contest_patterns = patterns('oioioi.testspackages.views',
    url(r'^tests/$', 'tests_view', name='tests'),
    url(r'^tests/(?P<package_id>\d+)/$', 'test_view', name='test'),
)

urlpatterns = patterns('oioioi.testspackages.views',
    url(r'^c/(?P<contest_id>[a-z0-9_-]+)/', include(contest_patterns)),
)
