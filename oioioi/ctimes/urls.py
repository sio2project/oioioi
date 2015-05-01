from django.conf.urls import patterns, include, url

urlpatterns = patterns('oioioi.ctimes.views',
    url(r'^ctimes/$', 'ctimes_view', name='ctimes')
)
