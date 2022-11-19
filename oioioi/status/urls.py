from django.urls import re_path

from oioioi.status import views

app_name = 'status'

urlpatterns = [
    re_path(r'^status/$', views.get_status_view, name='get_status'),
]
