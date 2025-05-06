from django.urls import path

from oioioi.status import views

app_name = 'status'

urlpatterns = [
    path('status/', views.get_status_view, name='get_status'),
]
