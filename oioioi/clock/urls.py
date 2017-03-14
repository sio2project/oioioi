from django.conf.urls import url

from oioioi.clock import views

urlpatterns = [
    url(r'^admin/time/$', views.admin_time, name='admin_time'),
]
