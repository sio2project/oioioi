from django.urls import re_path

from oioioi.mp import views

app_name = 'mp'

contest_patterns = [
    #re_path(r'^contest_info/$', views.contest_info_view, name='contest_info')
]
