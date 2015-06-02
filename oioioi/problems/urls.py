from django.conf.urls import patterns, include, url


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

    url(r'^problem/(?P<problem_instance_id>[a-z0-9_-]+)/models$',
        'model_solutions_view',
        name='model_solutions'),
    url(r'^problem/(?P<problem_instance_id>[a-z0-9_-]+)/models/rejudge$',
        'rejudge_model_solutions_view',
        name='model_solutions_rejudge'),

    url(r'^problemset/$', 'problemset_main_view', name='problemset_main'),
    url(r'^problemset/myproblems/$', 'problemset_my_problems_view',
        name='problemset_my_problems'),
    url(r'^problemset/problem/(?P<site_key>[0-9a-zA-Z-_=]+)/',
        include(problem_site_patterns)),
    url(r'^problemset/add_or_update/', 'problemset_add_or_update_problem_view',
        name='problemset_add_or_update'),
    url(r'^get_report_HTML/(?P<submission_id>\d+)/$', 'get_report_HTML_view',
        name='get_report_HTML'),
    url(r'^s_wc/(?P<submission_id>\d+)/$', 'submission_without_contest_view',
        name='submission_without_contest'),
    url(r'^s_wc/(?P<submission_id>\d+)/rejudge/$',
        'rejudge_submission_without_contest_view',
        name='rejudge_submission_without_contest'),
    url(r'^s_wc/(?P<submission_id>\d+)/change_kind/(?P<kind>\w+)/$',
        'change_submission_kind_without_contest_view',
        name='change_submission_kind_without_contest'),

    url(r'^get_tag_hints/$', 'get_tag_hints_view', name='get_tag_hints'),
)
