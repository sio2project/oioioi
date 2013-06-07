from django.conf.urls import patterns, url

urlpatterns = patterns('oioioi.sinolpack.views',
    url(r'^sinolpack/extra/(?P<file_id>\d+)/$', 'download_extra_file_view',
        name='download_extra_file'),
)
