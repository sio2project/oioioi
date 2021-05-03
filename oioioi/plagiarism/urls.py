from django.conf.urls import url

from oioioi.plagiarism import views

app_name = 'plagiarism'

contest_patterns = [
    url(
        r'^moss_submit/$',
        views.moss_submit,
        name='moss_submit',
    ),
]
