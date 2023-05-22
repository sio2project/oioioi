from django.urls import re_path

from oioioi.oireports import views

app_name = 'oireports'

contest_patterns = [
    re_path(r'^oireports/$', views.oireports_view, name='oireports'),
    re_path(
        r'^get_report_users/$', views.get_report_users_view, name='get_report_users'
    ),
]
