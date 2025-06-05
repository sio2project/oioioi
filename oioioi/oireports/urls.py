from django.urls import path

from oioioi.oireports import views

app_name = 'oireports'

contest_patterns = [
    path('oireports/', views.oireports_view, name='oireports'),
    path('get_report_users/', views.get_report_users_view, name='get_report_users'),
]
