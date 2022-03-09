from django.urls import re_path

from oioioi.mailsubmit import views

app_name = 'mailsubmit'

contest_patterns = [
    re_path(r'^mailsubmit/$', views.mailsubmit_view, name='mailsubmit'),
    re_path(
        r'^mailsubmit/accept/$',
        views.accept_mailsubmission_view,
        name='accept_mailsubmission_default',
    ),
    re_path(
        r'^mailsubmit/accept/(?P<mailsubmission_id>\d+)/'
        r'(?P<mailsubmission_hash>[a-z0-9]+)/$',
        views.accept_mailsubmission_view,
        name='accept_mailsubmission',
    ),
]
