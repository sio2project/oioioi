from django.urls import path

from oioioi.exportszu import views

app_name = 'exportszu'

contest_patterns = [
    path(
        'export_submissions/',
        views.export_submissions_view,
        name='export_submissions',
    ),
]
