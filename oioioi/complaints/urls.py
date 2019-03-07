from django.conf.urls import url

from oioioi.complaints import views

app_name = 'complaints'

contest_patterns = [
    url(r'^complaints/$', views.add_complaint_view, name='add_complaint'),
    url(r'^complaint_sent/$', views.complaint_sent, name='complaint_sent'),
]
