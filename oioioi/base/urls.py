from django.conf.urls import patterns, url

urlpatterns = patterns('oioioi.base.views',
    url(r'^$', 'index_view', name='index'),
    url(r'^force_error$', 'force_error_view'),
)
