from django.conf.urls import patterns, include, url

contest_patterns = patterns('oioioi.zeus.views',
    url(r'^s/(?P<submission_id>\d+)/ztr/library/$',
        'show_library_file_view', name='zeus_get_testrun_library'),
    url(r'^s/(?P<submission_id>\d+)/ztr/library/download/$',
        'download_library_file_view', name='zeus_download_testrun_library'),
    url(r'^s/(?P<submission_id>\d+)/ztr/output/$',
        'show_output_file_view', name='zeus_get_testrun_output'),
    url(r'^s/(?P<submission_id>\d+)/ztr/output/(?P<testrun_report_id>\d+)/$',
        'show_output_file_view', name='zeus_get_specific_testrun_output'),
    url(r'^s/(?P<submission_id>\d+)/ztr/output/download/$',
        'download_output_file_view', name='zeus_download_testrun_output'),
    url(r'^s/(?P<submission_id>\d+)/ztr/output/'
            r'(?P<testrun_report_id>\d+)/download/$',
        'download_output_file_view',
        name='zeus_download_specific_testrun_output'),
)

urlpatterns = patterns('oioioi.testrun.views',
    url(r'^c/(?P<contest_id>[a-z0-9_-]+)/', include(contest_patterns)),
)
