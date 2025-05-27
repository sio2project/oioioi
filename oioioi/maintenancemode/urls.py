from django.urls import path

from oioioi.maintenancemode import views

app_name = 'maintenancemode'

urlpatterns = [
    path('maintenance/', views.maintenance_view, name='maintenance'),
    path(
        'set_maintenance_mode/',
        views.set_maintenance_mode_view,
        name='set_maintenance_mode',
    ),
]
