from django.conf.urls import patterns, url

urlpatterns = patterns('oioioi.clock.views',
    url(r'^round_times/$', 'get_times_view', name='get_times_view'),
    url(r'^admin/time/(?P<path>.*)/$', 'admin_time', name='admin_time'),
)
