from django.conf.urls import patterns, include, url

contest_patterns = patterns('oioioi.contests.views',
    url(r'^$', 'default_contest_view', name='default_contest_view'),
    url(r'^p$', 'problems_list_view', name='problems_list'),
    url(r'^p/(?P<problem_instance>[a-z0-9_-]+)$', 'problem_statement_view',
        name='problem_statement'),
    url(r'^submit$', 'submit_view', name='submit'),
    url(r'^submissions$', 'my_submissions_view', name='my_submissions'),
    url(r'^s/(?P<submission_id>\d+)$', 'submission_view',
        name='submission'),
    url(r'^s/(?P<submission_id>\d+)/rejudge$', 'rejudge_submission_view',
        name='rejudge_submission'),
    url(r'^files$', 'files_view', name='contest_files'),
    url(r'^ca/(?P<attachment_id>\d+)$', 'contest_attachment_view',
        name='contest_attachment'),
    url(r'^pa/(?P<attachment_id>\d+)$', 'problem_attachment_view',
        name='problem_attachment'),
)

urlpatterns = patterns('oioioi.contests.views',
    url(r'^c/(?P<contest_id>[a-z0-9_-]+)/', include(contest_patterns)),
    url(r'^c/$', 'select_contest_view', name='select_contest'),
)
