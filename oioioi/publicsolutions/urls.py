from django.urls import path

from oioioi.publicsolutions import views

app_name = 'publicsolutions'

contest_patterns = [
    path('solutions/', views.list_solutions_view, name='list_solutions'),
    path(
        'solutions/publish/', views.publish_solutions_view, name='publish_solutions'
    ),
    path(
        'solutions/publish/<int:submission_id>/',
        views.publish_solution_view,
        name='publish_solution',
    ),
    path(
        'solutions/unpublish/<int:submission_id>/',
        views.unpublish_solution_view,
        name='unpublish_solution',
    ),
]
