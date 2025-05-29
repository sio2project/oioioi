from django.urls import path
from django.urls import re_path

from oioioi.mailsubmit import views

app_name = 'mailsubmit'

contest_patterns = [
    path('mailsubmit/', views.mailsubmit_view, name='mailsubmit'),
    path(
        'mailsubmit/accept/',
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
