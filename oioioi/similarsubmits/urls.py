from django.urls import path

from oioioi.similarsubmits import views

app_name = 'similarsubmits'

contest_patterns = [
    path(
        '<int:entry_id>/mark_guilty/', views.mark_guilty_view, name='mark_guilty'
    ),
    path(
        '<int:entry_id>/mark_not_guilty/',
        views.mark_not_guilty_view,
        name='mark_not_guilty',
    ),
    path('bulk_add/', views.bulk_add_similarities_view, name='bulk_add_similarities'),
]
