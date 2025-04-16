from django.urls import path

from oioioi.welcomepage import views

app_name = 'welcomepage'

noncontest_patterns = [
    path('welcome/', views.welcome_page_view, name='welcome_page'),
    path('edit_welcome_page/', views.edit_welcome_page_view, name='edit_welcome_page'),
    path('delete_welcome_page/', views.delete_welcome_page_view, name='delete_welcome_page'),
]
