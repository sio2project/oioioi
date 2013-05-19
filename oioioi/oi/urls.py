from django.conf.urls import patterns, url

urlpatterns = patterns('oioioi.oi.views',
    url(r'^oi/cities/$', 'cities_view'),
    url(r'^oi/schools/$', 'schools_view'),
)
