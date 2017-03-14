from django.conf.urls import url

from oioioi.dashboard import views
from oioioi.dashboard.contest_dashboard import contest_dashboard_view

contest_patterns = [
    url(r'^dashboard-message/$', views.dashboard_message_edit_view,
        name='dashboard_message_edit'),
    url(r'^dashboard/$', contest_dashboard_view, name='contest_dashboard'),
]
