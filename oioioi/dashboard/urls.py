from django.conf.urls import patterns, include, url

contest_patterns = patterns('oioioi.dashboard.views',
    url(r'^dashboard-message/$', 'dashboard_message_edit_view',
        name='dashboard_message_edit'),
)

contest_patterns += [
    url(r'^dashboard/$',
        'oioioi.dashboard.contest_dashboard.contest_dashboard_view',
        name='contest_dashboard'),
]
