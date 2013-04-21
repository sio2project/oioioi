from django.conf.urls import url, patterns


urlpatterns = patterns('oioioi.status.views',
    url(r'^c/(?P<contest_id>[a-z0-9_-]+)/status/$', 'get_status_view',
            name='get_contest_status'),
    url(r'^status/$', 'get_status_view', name='get_status'),
)

