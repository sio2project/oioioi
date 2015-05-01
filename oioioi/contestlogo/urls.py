from django.conf.urls import patterns, url, include

contest_patterns = patterns('oioioi.contestlogo.views',
    url(r'^logo/$', 'logo_image_view', name='logo_image_view'),
    url(r'^icons/(?P<icon_id>\d+)/$', 'icon_image_view',
        name='icon_image_view'),
)
