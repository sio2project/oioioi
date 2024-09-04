from django.urls import re_path

from oioioi.su import views

app_name = 'su'

noncontest_patterns = [
    re_path(r'^su/$', views.su_view, name='su'),
    re_path(
        r'^get_suable_usernames/', views.get_suable_users_view, name='get_suable_users'
    ),
    re_path(r'^su_reset/$', views.su_reset_view, name='su_reset'),
]

contest_patterns = [
    re_path(r'^su/$', views.su_view, name='su'),
    re_path(
        r'^get_suable_usernames/', views.get_suable_users_view, name='get_suable_users'
    ),
    re_path(r'^su_method_not_allowed/', views.method_not_allowed_view, name='su_method_not_allowed'),
]
