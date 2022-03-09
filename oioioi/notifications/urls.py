from django.urls import re_path

from oioioi.notifications import views

app_name = 'notifications'

noncontest_patterns = [
    re_path(
        r'^notifications/authenticate/$',
        views.notifications_authenticate_view,
        name='notifications_authenticate',
    ),
]
