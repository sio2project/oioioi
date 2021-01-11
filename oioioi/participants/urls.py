from django.conf.urls import url

from oioioi.participants import views

app_name = 'participants'

contest_patterns = [
    url(r'^register/$', views.registration_view, name='participants_register'),
    url(r'^unregister/$', views.unregistration_view, name='participants_unregister'),
    url(r'^participants_data/$', views.participants_data, name='participants_data'),
    url(
        r'^participants_data_csv/$',
        views.participants_data_csv,
        name='participants_data_csv',
    ),
]
