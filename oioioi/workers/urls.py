from django.urls import re_path

from oioioi.workers import views

app_name = 'workers'

urlpatterns = [
    re_path(r'^workers/$', views.show_info_about_workers, name='show_workers'),
    re_path(r'^workers/load.json$', views.get_load_json, name='get_load_json'),
]
