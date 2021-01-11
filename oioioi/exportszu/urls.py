from django.conf.urls import url

from oioioi.exportszu import views

app_name = 'exportszu'

contest_patterns = [
    url(
        r'^export_submissions/$',
        views.export_submissions_view,
        name='export_submissions',
    ),
]
