from django.urls import path

from oioioi.ctimes import views

app_name = 'ctimes'

urlpatterns = [path('ctimes/', views.ctimes_view, name='ctimes')]
