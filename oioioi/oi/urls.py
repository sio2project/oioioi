from django.conf.urls import patterns, url

urlpatterns = patterns('oioioi.oi.views',
    url(r'^oi/cities/$', 'cities_view'),
    url(r'^oi/schools/$', 'schools_view'),
    url(r'^oi/schools/similar/$', 'schools_similar_view',
        name='schools_similar'),
    url(r'^oi/schools/add/$', 'add_school_view', name='add_school'),
    url(r'^oi/schools/choose/(?P<school_id>[0-9]+)/$', 'choose_school_view',
        name='choose_school'),
)
