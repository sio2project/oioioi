from django.urls import path

from oioioi.timeline import views

app_name = 'timeline'

contest_patterns = [
    path('admin_profile/timeline/', views.timeline_view, name='timeline_view'),
]
