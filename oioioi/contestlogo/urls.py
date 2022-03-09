from django.urls import re_path

from oioioi.contestlogo import views

app_name = 'contestlogo'

contest_patterns = [
    re_path(r'^logo/$', views.logo_image_view, name='logo_image_view'),
    re_path(r'^icons/(?P<icon_id>\d+)/$', views.icon_image_view, name='icon_image_view'),
]
