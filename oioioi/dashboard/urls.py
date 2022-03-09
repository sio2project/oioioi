from django.urls import re_path

from oioioi.dashboard import views
from oioioi.dashboard.contest_dashboard import contest_dashboard_view

app_name = 'dashboard'

contest_patterns = [
    re_path(
        r'^dashboard-message/$',
        views.dashboard_message_edit_view,
        name='dashboard_message_edit',
    ),
    re_path(r'^dashboard/$', contest_dashboard_view, name='contest_dashboard'),
]
