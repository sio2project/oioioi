from django.conf import settings
from django.urls import path
from django.urls import include, re_path
from oioioi.problems import api, views

app_name = 'problems'

problem_site_patterns = [
    path('site/', views.problem_site_view, name='problem_site'),
    path(
        'site/<path:path>',
        views.problem_site_statement_zip_view,
        name='problem_site_statement_zip',
    ),
    path(
        'statement/',
        views.problem_site_external_statement_view,
        name='problem_site_external_statement',
    ),
    path(
        'attachment/<int:attachment_id>/',
        views.problem_site_external_attachment_view,
        name='problem_site_external_attachment',
    ),
]

urlpatterns = [
    path(
        'statement/<int:statement_id>/',
        views.show_statement_view,
        name='show_statement',
    ),
    path(
        'problem_attachment/<int:attachment_id>/',
        views.show_problem_attachment_view,
        name='show_problem_attachment',
    ),
    path(
        'problem_package/<int:package_id>/',
        views.download_problem_package_view,
        name='download_package',
    ),
    re_path(
        r'^problem_package/(?P<package_id>\d+)/download_file/(?P<file_name>[0-9a-zA-Z-_=\.\/]+)/$',
        views.download_problem_package_file_view,
        name='download_package_file',
    ),
    path(
        'package_traceback/<int:package_id>/',
        views.download_package_traceback_view,
        name='download_package_traceback',
    ),
    path(
        'problems/add',
        views.add_or_update_problem_view,
        name='add_or_update_problem',
    ),
    re_path(
        r'^problem/(?P<problem_instance_id>[a-z0-9_-]+)/models$',
        views.model_solutions_view,
        name='model_solutions',
    ),
    re_path(
        r'^problem/(?P<problem_instance_id>[a-z0-9_-]+)/models/rejudge$',
        views.rejudge_model_solutions_view,
        name='model_solutions_rejudge',
    ),
    path(
        'problemset/myproblems/',
        views.problemset_my_problems_view,
        name='problemset_my_problems',
    ),
    path(
        'problemset/shared_with_me/',
        views.problemset_shared_with_me_view,
        name='problemset_shared_with_me',
    ),
    path(
        'problemset/all_problems/',
        views.problemset_all_problems_view,
        name='problemset_all_problems',
    ),
    re_path(
        r'^problemset/problem/(?P<site_key>[0-9a-zA-Z-_=]+)/',
        include(problem_site_patterns),
    ),
    re_path(
        r'^problemset/problem/(?P<site_key>[0-9a-zA-Z-_=]+)/add_to_contest/$',
        views.problemset_add_to_contest_view,
        name='problemset_add_to_contest',
    ),
    re_path(
        r'^problemset/add_or_update/',
        views.problemset_add_or_update_problem_view,
        name='problemset_add_or_update',
    ),
    path(
        'get_report_HTML/<int:submission_id>/',
        views.get_report_HTML_view,
        name='get_report_HTML',
    ),
    path(
        'get_report_row_begin_HTML/<int:submission_id>/',
        views.get_report_row_begin_HTML_view,
        name='get_report_row_begin_HTML',
    ),
    path('task_archive/', views.task_archive_view, name='task_archive'),
    re_path(
        r'^task_archive/(?P<origin_tag>[0-9a-z-]+)/',
        views.task_archive_tag_view,
        name='task_archive_tag',
    ),
    re_path(
        r'^get_search_hints/(?P<view_type>public|my|all)/$',
        views.get_search_hints_view,
        name='get_search_hints',
    ),
    path(
        'get_selected_origintag_hints/',
        views.get_selected_origintag_hints_view,
        name='get_selected_origintag_hints',
    ),
    path(
        'get_origininfocategory_hints/',
        views.get_origininfocategory_hints_view,
        name='get_origininfocategory_hints',
    ),
    path(
        'latest_submissions/', views.get_last_submissions, name='latest_submissions'
    ),
    path(
        'get_algorithm_tag_proposal_hints/',
        views.get_algorithm_tag_proposal_hints_view,
        name='get_algorithm_tag_proposal_hints',
    ),
    path(
        'get_algorithm_tag_label/',
        views.get_algorithm_tag_label_view,
        name='get_algorithm_tag_label',
    ),
    re_path(r'^save_proposals/', views.save_proposals_view,
            name='save_proposals'),
]

noncontest_patterns = [
    path('problemset/', views.problemset_main_view, name='problemset_main')
]

if settings.USE_API:
    noncontest_patterns += [
        path(
            'api/problems/package_upload/',
            api.PackageUploadView.as_view(),
            name='api_package_upload',
        ),
        path(
            'api/problems/package_upload/<int:package_id>/',
            api.PackageUploadQueryView.as_view(),
            name='api_package_upload_query',
        ),
        path(
            'api/problems/package_reupload/',
            api.PackageReuploadView.as_view(),
            name='api_package_reupload',
        ),
    ]
