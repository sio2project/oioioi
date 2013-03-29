from django.conf.urls import patterns, include, url

contest_patterns = patterns('oioioi.complaints.views',
    url(r'^complaints$', 'add_complaint', name='complaints'),
    url(r'^complaint_sent$', 'complaint_sent', name='complaint_sent'),
)

urlpatterns = patterns('oioioi.complaints.views',
    url(r'^c/(?P<contest_id>[a-z0-9_-]+)/', include(contest_patterns)),
)
