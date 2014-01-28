from django.conf.urls import patterns, url


urlpatterns = patterns('oioioi.timeline.views',
    url(r'^admin/timeline/$', 'timeline_view', name='timeline_view'),
)
