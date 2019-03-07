from django.conf.urls import url

from oioioi.maintenancemode import views

app_name = 'maintenancemode'

urlpatterns = [
    url(r'^maintenance/$', views.maintenance_view, name='maintenance'),
    url(r'^set_maintenance_mode/$', views.set_maintenance_mode_view,
        name='set_maintenance_mode'),
]
