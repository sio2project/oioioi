from django.conf.urls import patterns, include, url

contest_patterns = patterns('oioioi.oisubmit.views',
    url(r'^oisubmit/$', 'oisubmit_view', name='oisubmit'),
)

urlpatterns = patterns('oioioi.oisubmit.views',
    url(r'^c/(?P<contest_id>[a-z0-9_-]+)/', include(contest_patterns)),
)
