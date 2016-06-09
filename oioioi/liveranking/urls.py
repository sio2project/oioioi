from django.conf.urls import patterns, include, url

contest_patterns = patterns('oioioi.liveranking.views',
    url(r'^liveranking/(?P<round_id>\d+)/$', 'liveranking_auto_view',
        name='liveranking_auto'),
    url(r'^liveranking/(?P<round_id>\d+)/simple/$', 'liveranking_simple_view',
        name='liveranking_simple'),
    url(r'^liveranking/(?P<round_id>\d+)/auto_donuts/$',
        'liveranking_autoDonuts_view', name='liveranking_autoDonuts'),
    url(r'^liveranking/(?P<round_id>\d+)/simple_donuts/$',
        'liveranking_simpleDonuts_view', name='liveranking_simpleDonuts'),

    url(r'^liveranking/$', 'liveranking_auto_view',
        name='liveranking_auto_no_round'),
    url(r'^liveranking/simple/$', 'liveranking_simple_view',
        name='liveranking_simple_no_round'),
    url(r'^liveranking/auto_donuts/$', 'liveranking_autoDonuts_view',
        name='liveranking_autoDonuts_no_round'),
    url(r'^liveranking/simple_donuts/$', 'liveranking_simpleDonuts_view',
        name='liveranking_simpleDonuts_no_round'),
)

urlpatterns = patterns('oioioi.liveranking.views',
    url(r'^c/(?P<contest_id>[a-z0-9_-]+)/', include(contest_patterns)),
)
