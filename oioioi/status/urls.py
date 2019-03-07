from django.conf.urls import url

from oioioi.status import views

app_name = 'status'

urlpatterns = [
    url(r'^status/$', views.get_status_view, name='get_status'),
]
