from django.conf.urls import patterns, include, url

contest_patterns = patterns('oioioi.problems.views',
    url(r'^problems/add$', 'add_or_update_problem_view',
        name='add_or_update_contest_problem'),
)

urlpatterns = patterns('oioioi.problems.views',
    url(r'^statement/(?P<statement_id>\d+)/$', 'show_statement_view',
        name='show_statement'),
    url(r'^problem_attachment/(?P<attachment_id>\d+)/$',
        'show_problem_attachment_view', name='show_problem_attachment'),
    url(r'^problem_package/(?P<package_id>\d+)/$',
        'download_problem_package_view', name='download_package'),
    url(r'^package_traceback/(?P<package_id>\d+)/$',
        'download_package_traceback_view', name='download_package_traceback'),

    url(r'^problems/add$', 'add_or_update_problem_view',
        name='add_or_update_problem'),
    url(r'^c/(?P<contest_id>[a-z0-9_-]+)/', include(contest_patterns)),
)
