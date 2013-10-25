from django.conf.urls import patterns, url

urlpatterns = patterns('oioioi.ctimes.views',
    url(r'^ctimes/$', 'ctimes_view', name='ctimes')
)
