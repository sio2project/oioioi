from django.urls import path

from oioioi.testspackages import views

app_name = 'testspackages'

contest_patterns = [
    path('tests/<int:package_id>/', views.test_view, name='test'),
]

noncontest_patterns = [
    path(
        'tests/<int:package_id>/',
        views.test_view_for_problem,
        name='test_for_problem',
    ),
]
