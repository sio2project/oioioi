from django.conf.urls import patterns, include, url

contest_patterns = patterns('oioioi.oireports.views',
    # 'report_options' is for picking contest, region and type
    url(r'^report_options/$', 'report_options_view', \
         name='report_options'),
    url(r'^pdfreport/$', 'pdfreport_view', name='pdfreport'),
    url(r'^xmlreport/$', 'xmlreport_view', name='xmlreport'),
)

urlpatterns = patterns('oioioi.oireports.views',
    url(r'^c/(?P<contest_id>[a-z0-9_-]+)/', include(contest_patterns)),
)
