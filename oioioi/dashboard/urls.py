from django.conf.urls import patterns, include, url

contest_patterns = patterns('oioioi.dashboard.views',
    url(r'^dashboard/$', 'contest_dashboard_view', name='contest_dashboard'),
)

urlpatterns = patterns('oioioi.dashboard.views',
    url(r'^c/(?P<contest_id>[a-z0-9_-]+)/', include(contest_patterns)),
)
