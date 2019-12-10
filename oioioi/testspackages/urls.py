from django.conf.urls import url

from oioioi.testspackages import views

app_name = 'testspackages'

contest_patterns = [
    url(r'^tests/(?P<package_id>\d+)/$', views.test_view, name='test'),
]
