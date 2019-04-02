from django.conf.urls import url

from oioioi.prizes import views

app_name = 'prizes'

contest_patterns = [
    url(r'^prizes/$', views.prizes_view, name='default_prizes'),
    url(r'^prizes/(?P<key>\d+)/$', views.prizes_view, name='prizes'),
    url(r'^prizes/download_report/(?P<pg_id>\d+)/$',
        views.download_report_view, name='download_report'),
]
