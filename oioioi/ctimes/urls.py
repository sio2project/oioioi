from django.conf.urls import url

from oioioi.ctimes import views

urlpatterns = [
    url(r'^ctimes/$', views.ctimes_view, name='ctimes')
]
