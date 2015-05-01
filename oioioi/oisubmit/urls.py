from django.conf.urls import patterns, include, url

contest_patterns = patterns('oioioi.oisubmit.views',
    url(r'^oisubmit/$', 'oisubmit_view', name='oisubmit'),
)
