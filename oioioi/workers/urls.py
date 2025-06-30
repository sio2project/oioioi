from django.urls import path
from django.urls import re_path

from oioioi.workers import views

app_name = 'workers'

urlpatterns = [
    path('workers/', views.show_info_about_workers, name='show_workers'),
    re_path(r'^workers/load.json$', views.get_load_json, name='get_load_json'),
]
