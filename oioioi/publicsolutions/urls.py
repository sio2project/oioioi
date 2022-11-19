from django.urls import re_path

from oioioi.publicsolutions import views

app_name = 'publicsolutions'

contest_patterns = [
    re_path(r'^solutions/$', views.list_solutions_view, name='list_solutions'),
    re_path(
        r'^solutions/publish/$', views.publish_solutions_view, name='publish_solutions'
    ),
    re_path(
        r'^solutions/publish/(?P<submission_id>\d+)/$',
        views.publish_solution_view,
        name='publish_solution',
    ),
    re_path(
        r'^solutions/unpublish/(?P<submission_id>\d+)/$',
        views.unpublish_solution_view,
        name='unpublish_solution',
    ),
]
