from django.urls import re_path

from oioioi.plagiarism import views

app_name = 'plagiarism'

contest_patterns = [
    re_path(
        r'^moss_submit/$',
        views.moss_submit,
        name='moss_submit',
    ),
]
