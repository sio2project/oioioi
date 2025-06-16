from django.urls import path

from oioioi.participants import views

app_name = 'participants'

contest_patterns = [
    path('register/', views.registration_view, name='participants_register'),
    path('unregister/', views.unregistration_view, name='participants_unregister'),
    path('participants_data/', views.participants_data, name='participants_data'),
    path(
        'participants_data_csv/',
        views.participants_data_csv,
        name='participants_data_csv',
    ),
]
