from django.urls import re_path

from oioioi.exportszu import views

app_name = 'exportszu'

contest_patterns = [
    re_path(
        r'^export_submissions/$',
        views.export_submissions_view,
        name='export_submissions',
    ),
]
