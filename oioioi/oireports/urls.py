from django.conf.urls import url

from oioioi.oireports import views

app_name = 'oireports'

contest_patterns = [
    url(r'^oireports/$', views.oireports_view, name='oireports'),
    url(r'^get_report_users/$', views.get_report_users_view, name='get_report_users'),
]
