from django.conf.urls import patterns, url, include

contest_patterns = patterns('oioioi.contestlogo.views',
    url(r'^logo/$', 'logo_image_view', name='logo_image_view'),
    url(r'^icons/(?P<icon_id>\d+)/$', 'icon_image_view',
        name='icon_image_view'),
)

urlpatterns = patterns('oioioi.contestlogo.views',
    url(r'^c/(?P<contest_id>[a-z0-9_-]+)/', include(contest_patterns)),
)
