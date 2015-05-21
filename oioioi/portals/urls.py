from django.conf.urls import patterns, url
from oioioi.portals import views


noncontest_patterns = patterns('oioioi.portals.views',
    url(r'^create_portal/$', views.create_global_portal_view,
        name='create_global_portal'),
    url(r'^portal/(?P<portal_path>.*)$', views.global_portal_view,
        name='global_portal'),
    url(r'^users/(?P<username>[^/]+)/create_portal/$',
        views.create_user_portal_view, name='create_user_portal'),
    url(r'^users/(?P<username>[^/]+)/portal/(?P<portal_path>.*)$',
        views.user_portal_view, name='user_portal'),
    url(r'^move_node/$', views.move_node_view, name='move_node')
)
