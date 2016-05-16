from django.conf.urls import patterns, url

contest_patterns = patterns(
    'oioioi.simpleui.views',
    url(r'^contest-dashboard/$', 'contest_dashboard_view',
        name='teacher_contest_dashboard'),
    url(r'^contest-dashboard/(?P<round_pk>[0-9]+)/$',
        'contest_dashboard_view', name='teacher_contest_dashboard'),
)
