from django.urls import re_path

from oioioi.welcomepage import views

app_name = 'welcomepage'

noncontest_patterns = [
    re_path(r'^welcome/$', views.welcome_page_view, name='welcome_page'),
    re_path(r'^edit_welcome_page/$', views.edit_welcome_page_view, name='edit_welcome_page'),
    re_path(r'^delete_welcome_page/$', views.delete_welcome_page_view, name='delete_welcome_page'),
]
