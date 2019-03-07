from django.conf.urls import url

from oioioi.publicsolutions import views

app_name = 'publicsolutions'

contest_patterns = [
        url(r'^solutions/$', views.list_solutions_view,
            name='list_solutions'),
        url(r'^solutions/publish/$', views.publish_solutions_view,
            name='publish_solutions'),
        url(r'^solutions/publish/(?P<submission_id>\d+)/$',
            views.publish_solution_view, name='publish_solution'),
        url(r'^solutions/unpublish/(?P<submission_id>\d+)/$',
            views.unpublish_solution_view, name='unpublish_solution'),
]
