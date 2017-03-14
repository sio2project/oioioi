from django.conf.urls import url

from oioioi.oisubmit import views

contest_patterns = [
    url(r'^oisubmit/$', views.oisubmit_view, name='oisubmit'),
]
