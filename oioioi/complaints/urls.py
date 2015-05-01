from django.conf.urls import patterns, include, url

contest_patterns = patterns('oioioi.complaints.views',
    url(r'^complaints/$', 'add_complaint_view', name='add_complaint'),
    url(r'^complaint_sent/$', 'complaint_sent', name='complaint_sent'),
)
