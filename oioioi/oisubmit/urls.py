from django.urls import path

from oioioi.oisubmit import views

app_name = 'oisubmit'

contest_patterns = [
    path('oisubmit/', views.oisubmit_view, name='oisubmit'),
]
