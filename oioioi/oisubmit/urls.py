from django.urls import re_path

from oioioi.oisubmit import views

app_name = 'oisubmit'

contest_patterns = [
    re_path(r'^oisubmit/$', views.oisubmit_view, name='oisubmit'),
]
