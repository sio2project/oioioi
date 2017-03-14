from django.conf.urls import url

from oioioi.portals import views


noncontest_patterns = [
    url(r'^create_global_portal/$', views.create_global_portal_view,
        name='create_global_portal'),
    url(r'^portal/(?P<portal_path>.*)$', views.global_portal_view,
        name='global_portal'),
    url(r'^create_user_portal/$',
        views.create_user_portal_view, name='create_user_portal'),
    url(r'^~(?P<username>[^/]+)/(?P<portal_path>.*)$',
        views.user_portal_view, name='user_portal'),
    url(r'^move_node/$', views.move_node_view, name='move_node'),
    url(r'^render_markdown/$', views.render_markdown_view,
        name='render_markdown')
]
