from django.urls import path

from oioioi.contestlogo import views

app_name = 'contestlogo'

contest_patterns = [
    path('logo/', views.logo_image_view, name='logo_image_view'),
    path('icons/<int:icon_id>/', views.icon_image_view, name='icon_image_view'),
]
