from django.conf.urls import patterns, include, url


publicsolutions_patterns = patterns('oioioi.publicsolutions.views',
        url(r'^solutions/$', 'list_solutions_view', name='list_solutions'),
        url(r'^solutions/publish/$', 'publish_solutions_view',
            name='publish_solutions'),
        url(r'^solutions/publish/(?P<submission_id>\d+)/$',
            'publish_solution_view',
            name='publish_solution'),
        url(r'^solutions/unpublish/(?P<submission_id>\d+)/$',
            'unpublish_solution_view',
            name='unpublish_solution'),

)

urlpatterns = patterns('oioioi.publicsolutions.views',
    url(r'^c/(?P<contest_id>[a-z0-9_-]+)/', include(publicsolutions_patterns)),
)

