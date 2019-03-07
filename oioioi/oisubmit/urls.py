from django.conf.urls import url

from oioioi.oisubmit import views

app_name = 'oisubmit'

contest_patterns = [
    url(r'^oisubmit/$', views.oisubmit_view, name='oisubmit'),
]
