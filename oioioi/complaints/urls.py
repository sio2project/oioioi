from django.urls import path

from oioioi.complaints import views

app_name = 'complaints'

contest_patterns = [
    path('complaints/', views.add_complaint_view, name='add_complaint'),
    path('complaint_sent/', views.complaint_sent, name='complaint_sent'),
]
