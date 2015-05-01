from django.conf.urls import url, patterns

urlpatterns = patterns('oioioi.status.views',
    url(r'^status/$', 'get_status_view', name='get_status'),
)
