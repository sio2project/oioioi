from django.conf.urls import patterns, url


urlpatterns = patterns('oioioi.balloons.views',
    url(r'^balloon/(?P<color>[0-9a-f]{6}).svg$', 'balloon_svg_view',
        name='balloon_svg'),
    url(r'^balloons/$', 'balloons_view', name='balloons'),
    url(r'^balloons/body/$', 'balloons_body_view', name='balloons_body'),
)
