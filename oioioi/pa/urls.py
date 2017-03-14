from django.conf.urls import url

from oioioi.pa import views

contest_patterns = [
    url(r'^contest_info/$', views.contest_info_view, name='contest_info')
]
