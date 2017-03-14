from django.conf.urls import url

from oioioi.status import views


urlpatterns = [
    url(r'^status/$', views.get_status_view, name='get_status'),
]
