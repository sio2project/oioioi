from django.conf.urls import url

from oioioi.balloons import views

app_name = 'balloons'

contest_patterns = [
    url(
        r'^balloons/regenerate/$',
        views.balloons_regenerate_delivery_key_view,
        name='balloons_access_regenerate',
    ),
    url(
        r'^balloons/access/(?P<access_key>[0-9a-zA-Z-_=]{16})$',
        views.balloons_access_cookie_view,
        name='balloons_access_set_cookie',
    ),
    url(
        r'^balloons/delivery/panel/$',
        views.balloons_delivery_panel_view,
        name='balloons_delivery_panel',
    ),
    url(
        r'^balloons/delivery/new/$',
        views.get_new_balloon_requests_view,
        name='balloons_delivery_new',
    ),
    url(
        r'^balloons/delivery/set/$',
        views.set_balloon_delivered_view,
        name='balloons_set_delivered',
    ),
]

urlpatterns = [
    url(
        r'^balloon/(?P<color>[0-9a-f]{6}).svg$',
        views.balloon_svg_view,
        name='balloon_svg',
    ),
    url(r'^balloons/$', views.balloons_view, name='balloons'),
    url(r'^balloons/body/$', views.balloons_body_view, name='balloons_body'),
]
