from django.urls import re_path
from oioioi.simpleui import views

app_name = 'simpleui'

noncontest_patterns = [
    re_path(
        r'^user-dashboard/$', views.user_dashboard_view, name='simpleui_user_dashboard'
    )
]

contest_patterns = [
    re_path(
        r'^contest-dashboard/$',
        views.contest_dashboard_view,
        name='simpleui_contest_dashboard',
    ),
    re_path(
        r'^contest-dashboard/(?P<round_pk>[0-9]+)/$',
        views.contest_dashboard_view,
        name='simpleui_contest_dashboard',
    ),
    re_path(
        r'^problem-settings/(?P<problem_instance_id>\d+)/$',
        views.problem_settings,
        name='simpleui_problem_settings',
    ),
]
