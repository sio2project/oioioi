from django.urls import re_path

from oioioi.submitservice import views

app_name = 'submitservice'

contest_patterns = [
    re_path(r'^submitservice/submit/$', views.submit_view, name='submitservice_submit'),
    re_path(
        r'^submitservice/view_user_token/$',
        views.view_user_token,
        name='submitservice_view_user_token',
    ),
    re_path(
        r'^submitservice/clear_user_token/$',
        views.clear_user_token,
        name='submitservice_clear_user_token',
    ),
]
