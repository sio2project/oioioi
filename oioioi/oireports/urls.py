from django.conf.urls import patterns, include, url

contest_patterns = patterns('oioioi.oireports.views',
    url(r'^oireports/$', 'oireports_view', name='oireports'),
    url(r'^get_report_users/$', 'get_report_users_view',
        name='get_report_users'),
)

urlpatterns = patterns('oioioi.oireports.views',
    url(r'^c/(?P<contest_id>[a-z0-9_-]+)/', include(contest_patterns)),
)
