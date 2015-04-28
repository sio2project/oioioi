from django.conf.urls import patterns, url
from oioioi.portals import views


noncontest_patterns = patterns('oioioi.portals.views',
    url(r'^users/(?P<username>[^/]+)/create_portal/$',
        views.create_portal_view, name='create_portal'),
    url(r'^users/(?P<username>[^/]+)/portal/(?P<portal_path>.*)$',
        views.portal_view, name='portal'),
    url(r'^move_node/$', views.move_node_view, name='move_node')
)
