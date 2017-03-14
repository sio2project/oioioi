from django.conf.urls import url

from oioioi.exportszu import views

contest_patterns = [
    url(r'^export_submissions/$', views.export_submissions_view,
        name='export_submissions'),
]
