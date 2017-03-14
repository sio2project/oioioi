from django.conf.urls import url

from oioioi.notifications import views

noncontest_patterns = [
    url(r'^notifications/authenticate/$',
        views.notifications_authenticate_view,
        name='notifications_authenticate'),
]
