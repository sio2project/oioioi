from django.urls import path

from oioioi.plagiarism import views

app_name = 'plagiarism'

contest_patterns = [
    path(
        'moss_submit/',
        views.moss_submit,
        name='moss_submit',
    ),
]
