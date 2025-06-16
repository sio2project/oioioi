from django.urls import path

from oioioi.pa import views

app_name = 'pa'

contest_patterns = [
    path('contest_info/', views.contest_info_view, name='contest_info')
]
