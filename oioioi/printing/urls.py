from django.urls import re_path

from oioioi.printing import views

app_name = 'printing'

contest_patterns = [
    re_path(r'^printing/$', views.print_view, name='print_view'),
]
