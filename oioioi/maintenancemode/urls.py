from django.urls import re_path

from oioioi.maintenancemode import views

app_name = 'maintenancemode'

urlpatterns = [
    re_path(r'^maintenance/$', views.maintenance_view, name='maintenance'),
    re_path(
        r'^set_maintenance_mode/$',
        views.set_maintenance_mode_view,
        name='set_maintenance_mode',
    ),
]
