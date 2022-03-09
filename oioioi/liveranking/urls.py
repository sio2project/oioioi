from django.urls import re_path

from oioioi.liveranking import views

app_name = 'liveranking'

contest_patterns = [
    re_path(
        r'^liveranking/(?P<round_id>\d+)/$',
        views.liveranking_auto_view,
        name='liveranking_auto',
    ),
    re_path(
        r'^liveranking/(?P<round_id>\d+)/simple/$',
        views.liveranking_simple_view,
        name='liveranking_simple',
    ),
    re_path(
        r'^liveranking/(?P<round_id>\d+)/auto_donuts/$',
        views.liveranking_autoDonuts_view,
        name='liveranking_autoDonuts',
    ),
    re_path(
        r'^liveranking/(?P<round_id>\d+)/simple_donuts/$',
        views.liveranking_simpleDonuts_view,
        name='liveranking_simpleDonuts',
    ),
    re_path(
        r'^liveranking/$', views.liveranking_auto_view, name='liveranking_auto_no_round'
    ),
    re_path(
        r'^liveranking/simple/$',
        views.liveranking_simple_view,
        name='liveranking_simple_no_round',
    ),
    re_path(
        r'^liveranking/auto_donuts/$',
        views.liveranking_autoDonuts_view,
        name='liveranking_autoDonuts_no_round',
    ),
    re_path(
        r'^liveranking/simple_donuts/$',
        views.liveranking_simpleDonuts_view,
        name='liveranking_simpleDonuts_no_round',
    ),
]
