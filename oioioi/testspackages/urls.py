from django.urls import re_path

from oioioi.testspackages import views

app_name = 'testspackages'

contest_patterns = [
    re_path(r'^tests/(?P<package_id>\d+)/$', views.test_view, name='test'),
]

noncontest_patterns = [
    re_path(
        r'^tests/(?P<package_id>\d+)/$',
        views.test_view_for_problem,
        name='test_for_problem',
    ),
]
