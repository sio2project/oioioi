from django.conf.urls import patterns, url


urlpatterns = patterns('oioioi.maintenancemode.views',
    url(r'^maintenance/$', 'maintenance_view', name='maintenance'),
    url(r'^set_maintenance_mode/$', 'set_maintenance_mode_view',
        name='set_maintenance_mode'),
)
