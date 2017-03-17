from django.conf.urls import patterns, url

noncontest_patterns = patterns('oioioi.zeus.views',
    url(r'^s/(?P<saved_environ_id>[-:a-zA-Z0-9]+)/push_grade/'
        r'(?P<signature>[\w\d:-]+)/$',
        'push_grade', name='zeus_push_grade_callback'),
)
