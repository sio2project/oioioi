from django.urls import re_path

from oioioi.ctimes import views

app_name = 'ctimes'

urlpatterns = [re_path(r'^ctimes/$', views.ctimes_view, name='ctimes')]
