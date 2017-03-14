from django.conf.urls import url

from oioioi.submitservice import views

contest_patterns = [
    url(r'^submitservice/submit/$', views.submit_view,
        name='submitservice_submit'),
    url(r'^submitservice/view_user_token/$', views.view_user_token,
        name='submitservice_view_user_token'),
    url(r'^submitservice/clear_user_token/$', views.clear_user_token,
        name='submitservice_clear_user_token'),
]
