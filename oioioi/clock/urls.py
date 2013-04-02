from django.conf.urls import patterns, url

urlpatterns = patterns('oioioi.clock.views',
    url(r'^admin/time$', 'admin_time', name='admin_time'),
)
