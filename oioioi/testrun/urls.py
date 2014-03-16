from django.conf.urls import patterns, include, url

contest_patterns = patterns('oioioi.testrun.views',
    url(r'^testrun_submit/$', 'testrun_submit_view', name='testrun_submit'),
    url(r'^s/(?P<submission_id>\d+)/tr/input/$', 'show_input_file_view',
        name='get_testrun_input'),
    url(r'^s/(?P<submission_id>\d+)/tr/output/$', 'show_output_file_view',
        name='get_testrun_output'),
    url(r'^s/(?P<submission_id>\d+)/tr/output/(?P<testrun_report_id>\d+)/$',
        'show_output_file_view', name='get_specific_testrun_output'),
    url(r'^s/(?P<submission_id>\d+)/tr/input/download/$',
        'download_input_file_view', name='download_testrun_input'),
    url(r'^s/(?P<submission_id>\d+)/tr/output/download/$',
        'download_output_file_view', name='download_testrun_output'),
    url(r'^s/(?P<submission_id>\d+)/tr/output/'
            r'(?P<testrun_report_id>\d+)/download/$',
        'download_output_file_view', name='download_specific_testrun_output'),
)

urlpatterns = patterns('oioioi.testrun.views',
    url(r'^c/(?P<contest_id>[a-z0-9_-]+)/', include(contest_patterns)),
)
