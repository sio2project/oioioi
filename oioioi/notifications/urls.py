from django.urls import path

from oioioi.notifications import views

app_name = 'notifications'

noncontest_patterns = [
    path(
        'notifications/authenticate/',
        views.notifications_authenticate_view,
        name='notifications_authenticate',
    ),
]
