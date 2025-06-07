from django.urls import path
from django.urls import re_path

from oioioi.balloons import views

app_name = 'balloons'

contest_patterns = [
    path(
        'balloons/regenerate/',
        views.balloons_regenerate_delivery_key_view,
        name='balloons_access_regenerate',
    ),
    re_path(
        r'^balloons/access/(?P<access_key>[0-9a-zA-Z-_=]{16})$',
        views.balloons_access_cookie_view,
        name='balloons_access_set_cookie',
    ),
    path(
        'balloons/delivery/panel/',
        views.balloons_delivery_panel_view,
        name='balloons_delivery_panel',
    ),
    path(
        'balloons/delivery/new/',
        views.get_new_balloon_requests_view,
        name='balloons_delivery_new',
    ),
    path(
        'balloons/delivery/set/',
        views.set_balloon_delivered_view,
        name='balloons_set_delivered',
    ),
]

urlpatterns = [
    re_path(
        r'^balloon/(?P<color>[0-9a-f]{6}).svg$',
        views.balloon_svg_view,
        name='balloon_svg',
    ),
    path('balloons/', views.balloons_view, name='balloons'),
    path('balloons/body/', views.balloons_body_view, name='balloons_body'),
]
