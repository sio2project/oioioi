from django.conf.urls import url

from oioioi.clock import views

app_name = 'clock'

urlpatterns = [
    url(r'^admin/time/$', views.admin_time, name='admin_time'),
]
