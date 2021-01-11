from django.conf.urls import url

from oioioi.ctimes import views

app_name = 'ctimes'

urlpatterns = [url(r'^ctimes/$', views.ctimes_view, name='ctimes')]
