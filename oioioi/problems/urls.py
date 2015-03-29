from django.conf.urls import patterns, include, url

contest_patterns = patterns('oioioi.problems.views',
    url(r'^problems/add$', 'add_or_update_problem_view',
        name='add_or_update_contest_problem'),
)

problem_site_patterns = patterns('oioioi.problems.views',
    url(r'^site/$', 'problem_site_view', name='problem_site'),
    url(r'^site/(?P<path>.+)$', 'problem_site_statement_zip_view',
        name='problem_site_statement_zip'),

    url(r'^statement/$', 'problem_site_external_statement_view',
        name='problem_site_external_statement'),
    url(r'^attachment/(?P<attachment_id>\d+)/$',
        'problem_site_external_attachment_view',
        name='problem_site_external_attachment'),
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

    url(r'^problemset/$', 'problemset_main_view', name='problemset_main'),
    url(r'^problemset/myproblems/$', 'problemset_my_problems_view',
        name='problemset_my_problems'),
    url(r'^problemset/problem/(?P<site_key>[0-9a-zA-Z-_=]+)/',
        include(problem_site_patterns)),
)
