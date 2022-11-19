from django.conf.urls import url

from oioioi.quiz import views

contest_patterns = [
    url(r'^quiz/$', views.quiz_view, name='quiz'),
    url(r'^quiz/solve/$', views.quiz_solve, name='quiz_solve'),
]
