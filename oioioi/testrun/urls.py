from django.urls import re_path

from oioioi.testrun import views

app_name = 'testrun'

contest_patterns = [
    re_path(r'^testrun_submit/$', views.testrun_submit_view, name='testrun_submit'),
    re_path(
        r'^s/(?P<submission_id>\d+)/tr/input/$',
        views.show_input_file_view,
        name='get_testrun_input',
    ),
    re_path(
        r'^s/(?P<submission_id>\d+)/tr/output/$',
        views.show_output_file_view,
        name='get_testrun_output',
    ),
    re_path(
        r'^s/(?P<submission_id>\d+)/tr/output/(?P<testrun_report_id>\d+)/$',
        views.show_output_file_view,
        name='get_specific_testrun_output',
    ),
    re_path(
        r'^s/(?P<submission_id>\d+)/tr/input/download/$',
        views.download_input_file_view,
        name='download_testrun_input',
    ),
    re_path(
        r'^s/(?P<submission_id>\d+)/tr/output/download/$',
        views.download_output_file_view,
        name='download_testrun_output',
    ),
    re_path(
        r'^s/(?P<submission_id>\d+)/tr/output/'
        r'(?P<testrun_report_id>\d+)/download/$',
        views.download_output_file_view,
        name='download_specific_testrun_output',
    ),
]
