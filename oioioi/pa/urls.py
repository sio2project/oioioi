from django.conf.urls import patterns, include, url

contest_patterns = patterns('oioioi.pa.views',
    url(r'^contest_info/$', 'contest_info_view', name='contest_info')
)

urlpatterns = patterns('oioioi.pa.views',
    url(r'^c/(?P<contest_id>[a-z0-9_-]+)/', include(contest_patterns)),
)
