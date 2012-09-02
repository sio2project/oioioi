from django.conf.urls import patterns, include, url

contest_patterns = patterns('oioioi.programs.views',
    url(r'^s/(?P<submission_id>\d+)/source$', 'show_submission_source_view',
        name='show_submission_source'),
    url(r'^s/(?P<submission_id>\d+)/download$',
        'download_submission_source_view', name='download_submission_source'),
)

urlpatterns = patterns('oioioi.programs.views',
    url(r'^c/(?P<contest_id>[a-z0-9_-]+)/', include(contest_patterns)),
    url(r'^tests/(?P<test_id>\d+)/in$', 'download_input_file_view'),
    url(r'^tests/(?P<test_id>\d+)/out$', 'download_output_file_view'),
)
