from django.urls import re_path

from oioioi.pa import views

app_name = 'pa'

contest_patterns = [
    re_path(r'^contest_info/$', views.contest_info_view, name='contest_info')
]
