from django.conf.urls import patterns, url, include

contest_patterns = patterns('oioioi.balloons.views',
    url(r'^balloons/regenerate/$', 'balloons_regenerate_delivery_key_view',
        name='balloons_access_regenerate'),
    url(r'^balloons/access/(?P<access_key>[0-9a-zA-Z-_=]{16})$',
        'balloons_access_cookie_view', name='balloons_access_set_cookie'),
    url(r'^balloons/delivery/panel/$', 'balloons_delivery_panel_view',
        name='balloons_delivery_panel'),
    url(r'^balloons/delivery/new/$', 'get_new_balloon_requests_view',
        name='balloons_delivery_new'),
    url(r'^balloons/delivery/set/$', 'set_balloon_delivered_view',
        name='balloons_set_delivered'),
)

urlpatterns = patterns('oioioi.balloons.views',
    url(r'^balloon/(?P<color>[0-9a-f]{6}).svg$', 'balloon_svg_view',
        name='balloon_svg'),
    url(r'^balloons/$', 'balloons_view', name='balloons'),
    url(r'^balloons/body/$', 'balloons_body_view', name='balloons_body'),
)
