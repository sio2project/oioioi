from django.conf import settings
from django.urls import include, re_path
from oioioi.problems import api, views
from oioioi.problems.problem_site import problem_site_statement_zip_view

app_name = 'problems'

problem_site_patterns = [
    re_path(r'^site/$', views.problem_site_view, name='problem_site'),
    re_path(
        r'^site/(?P<path>.+)$',
        problem_site_statement_zip_view,
        name='problem_site_statement_zip',
    ),
    re_path(
        r'^statement/$',
        views.problem_site_external_statement_view,
        name='problem_site_external_statement',
    ),
    re_path(
        r'^attachment/(?P<attachment_id>\d+)/$',
        views.problem_site_external_attachment_view,
        name='problem_site_external_attachment',
    ),
]

urlpatterns = [
    re_path(
        r'^statement/(?P<statement_id>\d+)/$',
        views.show_statement_view,
        name='show_statement',
    ),
    re_path(
        r'^problem_attachment/(?P<attachment_id>\d+)/$',
        views.show_problem_attachment_view,
        name='show_problem_attachment',
    ),
    re_path(
        r'^problem_package/(?P<package_id>\d+)/$',
        views.download_problem_package_view,
        name='download_package',
    ),
    re_path(
        r'^problem_package/(?P<package_id>\d+)/download_file/(?P<file_name>[0-9a-zA-Z-_=\.\/]+)/$',
        views.download_problem_package_file_view,
        name='download_package_file',
    ),
    re_path(
        r'^package_traceback/(?P<package_id>\d+)/$',
        views.download_package_traceback_view,
        name='download_package_traceback',
    ),
    re_path(
        r'^problems/add$',
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
    re_path(
        r'^problemset/myproblems/$',
        views.problemset_my_problems_view,
        name='problemset_my_problems',
    ),
    re_path(
        r'^problemset/shared_with_me/$',
        views.problemset_shared_with_me_view,
        name='problemset_shared_with_me',
    ),
    re_path(
        r'problemset/all_problems/$',
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
    re_path(
        r'^get_report_HTML/(?P<submission_id>\d+)/$',
        views.get_report_HTML_view,
        name='get_report_HTML',
    ),
    re_path(
        r'^get_report_row_begin_HTML/(?P<submission_id>\d+)/$',
        views.get_report_row_begin_HTML_view,
        name='get_report_row_begin_HTML',
    ),
    re_path(r'^task_archive/$', views.task_archive_view, name='task_archive'),
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
    re_path(
        r'^get_selected_origintag_hints/$',
        views.get_selected_origintag_hints_view,
        name='get_selected_origintag_hints',
    ),
    re_path(
        r'^get_origininfocategory_hints/$',
        views.get_origininfocategory_hints_view,
        name='get_origininfocategory_hints',
    ),
    re_path(
        r'^latest_submissions/$', views.get_last_submissions, name='latest_submissions'
    ),
    re_path(
        r'^get_algorithm_tag_proposal_hints/$',
        views.get_algorithm_tag_proposal_hints_view,
        name='get_algorithm_tag_proposal_hints',
    ),
    re_path(
        r'^get_algorithm_tag_label/$',
        views.get_algorithm_tag_label_view,
        name='get_algorithm_tag_label',
    ),
    re_path(r'^save_proposals/', views.save_proposals_view, name='save_proposals'),
]

noncontest_patterns = [
    re_path(r'^problemset/$', views.problemset_main_view, name='problemset_main')
]

if settings.USE_API:
    noncontest_patterns += [
        re_path(
            r'^api/problems/package_upload/$',
            api.PackageUploadView.as_view(),
            name='api_package_upload',
        ),
        re_path(
            r'^api/problems/package_upload/(?P<package_id>\d+)/$',
            api.PackageUploadQueryView.as_view(),
            name='api_package_upload_query',
        ),
        re_path(
            r'^api/problems/package_reupload/$',
            api.PackageReuploadView.as_view(),
            name='api_package_reupload',
        ),
    ]
