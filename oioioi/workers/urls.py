from django.conf.urls import url

from oioioi.workers import views

app_name = 'workers'

urlpatterns = [
    url(r'^workers/$', views.show_info_about_workers, name='show_workers'),
    url(r'^workers/load.json$', views.get_load_json, name='get_load_json'),
]
