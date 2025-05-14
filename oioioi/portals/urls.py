from django.urls import path
from django.urls import re_path

from oioioi.portals import views

app_name = 'portals'

noncontest_patterns = [
    re_path(
        r'^portal/(?P<portal_path>.*)?$',
        views.redirect_old_global_portal,
        name='redirect_old_global_portal',
    ),
    path(
        'create_global_portal/',
        views.create_global_portal_view,
        name='create_global_portal',
    ),
    re_path(
        r'^p/(?P<link_name>[^/]+)/(?P<portal_path>.*)$',
        views.global_portal_view,
        name='global_portal',
    ),
    path(
        'create_user_portal/',
        views.create_user_portal_view,
        name='create_user_portal',
    ),
    re_path(
        r'^~(?P<username>[^/]+)/(?P<portal_path>.*)$',
        views.user_portal_view,
        name='user_portal',
    ),
    path('move_node/', views.move_node_view, name='move_node'),
    path('render_markdown/', views.render_markdown_view, name='render_markdown'),
    path(
        'portals_main_page/', views.portals_main_page_view, name='portals_main_page'
    ),
    path(
        'portals_main_page/<str:view_type>/',
        views.portals_main_page_view,
        name='portals_main_page_type',
    ),
]
