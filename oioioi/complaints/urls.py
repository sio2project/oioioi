from django.urls import re_path

from oioioi.complaints import views

app_name = 'complaints'

contest_patterns = [
    re_path(r'^complaints/$', views.add_complaint_view, name='add_complaint'),
    re_path(r'^complaint_sent/$', views.complaint_sent, name='complaint_sent'),
]
