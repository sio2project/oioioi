from django.conf.urls import url

from oioioi.liveranking import views


contest_patterns = [
    url(r'^liveranking/(?P<round_id>\d+)/$', views.liveranking_auto_view,
        name='liveranking_auto'),
    url(r'^liveranking/(?P<round_id>\d+)/simple/$',
        views.liveranking_simple_view, name='liveranking_simple'),
    url(r'^liveranking/(?P<round_id>\d+)/auto_donuts/$',
        views.liveranking_autoDonuts_view, name='liveranking_autoDonuts'),
    url(r'^liveranking/(?P<round_id>\d+)/simple_donuts/$',
        views.liveranking_simpleDonuts_view, name='liveranking_simpleDonuts'),

    url(r'^liveranking/$', views.liveranking_auto_view,
        name='liveranking_auto_no_round'),
    url(r'^liveranking/simple/$', views.liveranking_simple_view,
        name='liveranking_simple_no_round'),
    url(r'^liveranking/auto_donuts/$', views.liveranking_autoDonuts_view,
        name='liveranking_autoDonuts_no_round'),
    url(r'^liveranking/simple_donuts/$', views.liveranking_simpleDonuts_view,
        name='liveranking_simpleDonuts_no_round'),
]
