from django.conf.urls import patterns, include, url

contest_patterns = patterns('oioioi.mailsubmit.views',
    url(r'^mailsubmit/$', 'mailsubmit_view', name='mailsubmit'),
    url(r'^mailsubmit/accept/$', 'accept_mailsubmission_view',
        name='accept_mailsubmission_default'),
    url(r'^mailsubmit/accept/(?P<mailsubmission_id>\d+)/'
        r'(?P<mailsubmission_hash>[a-z0-9]+)/$', 'accept_mailsubmission_view',
        name='accept_mailsubmission'),
)
