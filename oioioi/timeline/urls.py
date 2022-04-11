from django.urls import re_path

from oioioi.timeline import views

app_name = 'timeline'

contest_patterns = [
    re_path(r'^admin_profile/timeline/$', views.timeline_view, name='timeline_view'),
]
