from django.conf.urls import include, url
from django.conf import settings

from oioioi.problems import views, api

app_name = 'problems'

problem_site_patterns = [
    url(r'^site/$', views.problem_site_view, name='problem_site'),
    url(r'^site/(?P<path>.+)$', views.problem_site_statement_zip_view,
        name='problem_site_statement_zip'),

    url(r'^statement/$', views.problem_site_external_statement_view,
        name='problem_site_external_statement'),
    url(r'^attachment/(?P<attachment_id>\d+)/$',
        views.problem_site_external_attachment_view,
        name='problem_site_external_attachment'),
]

urlpatterns = [
    url(r'^statement/(?P<statement_id>\d+)/$', views.show_statement_view,
        name='show_statement'),
    url(r'^problem_attachment/(?P<attachment_id>\d+)/$',
        views.show_problem_attachment_view, name='show_problem_attachment'),

    url(r'^problem_package/(?P<package_id>\d+)/$',
        views.download_problem_package_view, name='download_package'),
    url(r'^package_traceback/(?P<package_id>\d+)/$',
        views.download_package_traceback_view,
        name='download_package_traceback'),

    url(r'^problems/add$', views.add_or_update_problem_view,
        name='add_or_update_problem'),

    url(r'^problem/(?P<problem_instance_id>[a-z0-9_-]+)/models$',
        views.model_solutions_view, name='model_solutions'),
    url(r'^problem/(?P<problem_instance_id>[a-z0-9_-]+)/models/rejudge$',
        views.rejudge_model_solutions_view, name='model_solutions_rejudge'),

    url(r'^problemset/$', views.problemset_main_view, name='problemset_main'),
    url(r'^problemset/myproblems/$', views.problemset_my_problems_view,
        name='problemset_my_problems'),
    url(r'^problemset/shared_with_me/$', views.problemset_shared_with_me_view,
        name='problemset_shared_with_me'),
    url(r'problemset/all_problems/$', views.problemset_all_problems_view,
        name='problemset_all_problems'),
    url(r'^problemset/problem/(?P<site_key>[0-9a-zA-Z-_=]+)/',
        include(problem_site_patterns)),
    url(r'^problemset/problem/(?P<site_key>[0-9a-zA-Z-_=]+)/add_to_contest/$',
        views.problemset_add_to_contest_view,
        name='problemset_add_to_contest'),
    url(r'^problemset/add_or_update/',
        views.problemset_add_or_update_problem_view,
        name='problemset_add_or_update'),
    url(r'^get_report_HTML/(?P<submission_id>\d+)/$',
        views.get_report_HTML_view,
        name='get_report_HTML'),

    url(r'^task_archive/$', views.task_archive_view, name='task_archive'),
    url(r'^task_archive/(?P<origin_tag>[0-9a-z-]+)/',
        views.task_archive_tag_view, name='task_archive_tag'),

    url(r'^get_search_hints/(?P<view_type>public|my|all)/$', views.get_search_hints_view, name='get_search_hints'),
    url(r'^get_origininfocategory_hints/$', views.get_origininfocategory_hints_view, name='get_origininfocategory_hints'),
    url(r'^get_difficultytag_hints/$', views.get_difficultytag_hints_view, name='get_difficultytag_hints'),
    url(r'^get_algorithmtag_hints/$', views.get_algorithmtag_hints_view, name='get_algorithmtag_hints'),
    url(r'^get_tag_hints/$', views.get_tag_hints_view, name='get_tag_hints'),
    url(r'^latest_submissions/$', views.get_last_submissions, name='latest_submissions'),
    url(r'^get_tag_proposal_hints/$', views.get_tag_proposal_hints_view, name='get_tag_proposal_hints'),
    url(r'^get_tag_label/$', views.get_tag_label_view, name='get_tag_label'),

    url(r'^save_proposals/', views.save_proposals_view, name='save_proposals'),
]


noncontest_patterns = []

if settings.USE_API:
    noncontest_patterns += [
        url(r'^api/problems/package_upload/$', api.PackageUploadView.as_view(), name='api_package_upload'),
        url(r'^api/problems/package_reupload/$', api.PackageReuploadView.as_view(), name='api_package_reupload'),
    ]
