from django.conf.urls import patterns, include, url

contest_patterns = patterns('oioioi.submitservice.views',
    url(r'^submitservice/submit/$', 'submit_view',
        name='submitservice_submit'),
    url(r'^submitservice/view_user_token/$', 'view_user_token',
        name='submitservice_view_user_token'),
    url(r'^submitservice/clear_user_token/$', 'clear_user_token',
        name='submitservice_clear_user_token'),
)
