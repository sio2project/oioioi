from django.conf.urls import url

from oioioi.timeline import views

app_name = 'timeline'

contest_patterns = [
    url(r'^admin/timeline/$', views.timeline_view, name='timeline_view'),
]
