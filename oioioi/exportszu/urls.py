from django.conf.urls import patterns, url

contest_patterns = patterns('oioioi.exportszu.views',
    url(r'^export_submissions/$', 'export_submissions_view',
        name='export_submissions'),
)
