from django.conf.urls import url

from oioioi.timeline import views


contest_patterns = [
    url(r'^admin/timeline/$', views.timeline_view, name='timeline_view'),
]
