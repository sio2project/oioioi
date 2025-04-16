from django.urls import path

from oioioi.printing import views

app_name = 'printing'

contest_patterns = [
    path('printing/', views.print_view, name='print_view'),
]
