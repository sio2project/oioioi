from django.conf.urls import url

from oioioi.testrun import views


contest_patterns = [
    url(r'^testrun_submit/$', views.testrun_submit_view,
        name='testrun_submit'),
    url(r'^s/(?P<submission_id>\d+)/tr/input/$', views.show_input_file_view,
        name='get_testrun_input'),
    url(r'^s/(?P<submission_id>\d+)/tr/output/$', views.show_output_file_view,
        name='get_testrun_output'),
    url(r'^s/(?P<submission_id>\d+)/tr/output/(?P<testrun_report_id>\d+)/$',
        views.show_output_file_view, name='get_specific_testrun_output'),
    url(r'^s/(?P<submission_id>\d+)/tr/input/download/$',
        views.download_input_file_view, name='download_testrun_input'),
    url(r'^s/(?P<submission_id>\d+)/tr/output/download/$',
        views.download_output_file_view, name='download_testrun_output'),
    url(r'^s/(?P<submission_id>\d+)/tr/output/'
            r'(?P<testrun_report_id>\d+)/download/$',
        views.download_output_file_view,
        name='download_specific_testrun_output'),
]
