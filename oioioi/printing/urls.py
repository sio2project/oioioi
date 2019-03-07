from django.conf.urls import url

from oioioi.printing import views

app_name = 'printing'

contest_patterns = [
    url(r'^printing/$', views.print_view, name='print_view'),
]
