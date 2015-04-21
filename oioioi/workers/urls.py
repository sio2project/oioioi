from django.conf.urls import patterns, url

urlpatterns = patterns('oioioi.workers.views',
    url(r'^workers/$', 'show_info_about_workers', name='show_workers'),
)
