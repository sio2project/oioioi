from django.urls import path

from oioioi.clock import views

app_name = 'clock'

urlpatterns = [
    # Don't use the 'admin/' prefix, as that sometimes results in breakage.
    path('admin_time/', views.admin_time, name='admin_time'),
]
