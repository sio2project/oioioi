from django.conf.urls import patterns, include, url

contest_patterns = patterns('oioioi.pa.views',
    url(r'^contest_info/$', 'contest_info_view', name='contest_info')
)
