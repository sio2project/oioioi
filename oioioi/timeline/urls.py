from django.conf.urls import patterns, url


urlpatterns = patterns('oioioi.timeline.views',
    url(r'^admin/(?P<contest_id>[a-z0-9_-]+)/timeline/$', 'timeline_view',
        name='timeline_view'),
)
