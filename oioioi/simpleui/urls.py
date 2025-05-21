from django.urls import path
from oioioi.simpleui import views

app_name = 'simpleui'

noncontest_patterns = [
    path('user-dashboard/', views.user_dashboard_view, name='simpleui_user_dashboard')
]

contest_patterns = [
    path(
        'contest-dashboard/',
        views.contest_dashboard_view,
        name='simpleui_contest_dashboard',
    ),
    path(
        'contest-dashboard/<int:round_pk>/',
        views.contest_dashboard_view,
        name='simpleui_contest_dashboard',
    ),
    path(
        'problem-settings/<int:problem_instance_id>/',
        views.problem_settings,
        name='simpleui_problem_settings',
    ),
]
