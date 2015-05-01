from django.conf.urls import patterns, include, url

contest_patterns = patterns('oioioi.printing.views',
    url(r'^printing/$', 'print_view', name='print_view'),
)
