from django.conf.urls import url

from oioioi.contestlogo import views

app_name = 'contestlogo'

contest_patterns = [
    url(r'^logo/$', views.logo_image_view, name='logo_image_view'),
    url(r'^icons/(?P<icon_id>\d+)/$', views.icon_image_view, name='icon_image_view'),
]
