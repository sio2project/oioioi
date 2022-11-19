from django.urls import re_path

from oioioi.participants import views

app_name = 'participants'

contest_patterns = [
    re_path(r'^register/$', views.registration_view, name='participants_register'),
    re_path(r'^unregister/$', views.unregistration_view, name='participants_unregister'),
    re_path(r'^participants_data/$', views.participants_data, name='participants_data'),
    re_path(
        r'^participants_data_csv/$',
        views.participants_data_csv,
        name='participants_data_csv',
    ),
]
