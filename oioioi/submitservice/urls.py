from django.urls import path

from oioioi.submitservice import views

app_name = 'submitservice'

contest_patterns = [
    path('submitservice/submit/', views.submit_view, name='submitservice_submit'),
    path(
        'submitservice/view_user_token/',
        views.view_user_token,
        name='submitservice_view_user_token',
    ),
    path(
        'submitservice/clear_user_token/',
        views.clear_user_token,
        name='submitservice_clear_user_token',
    ),
]
