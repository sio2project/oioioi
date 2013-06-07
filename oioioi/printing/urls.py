from django.conf.urls import patterns, include, url

printing_patterns = patterns('oioioi.printing.views',
    url(r'^printing/$', 'print_view', name='print_view'),
)

urlpatterns = patterns('oioioi.contests.views',
    url(r'^c/(?P<contest_id>[a-z0-9_-]+)/', include(printing_patterns)),
)
