from django.urls import path

from oioioi.liveranking import views

app_name = 'liveranking'

contest_patterns = [
    path(
        'liveranking/<int:round_id>/',
        views.liveranking_auto_view,
        name='liveranking_auto',
    ),
    path(
        'liveranking/<int:round_id>/simple/',
        views.liveranking_simple_view,
        name='liveranking_simple',
    ),
    path(
        'liveranking/<int:round_id>/auto_donuts/',
        views.liveranking_autoDonuts_view,
        name='liveranking_autoDonuts',
    ),
    path(
        'liveranking/<int:round_id>/simple_donuts/',
        views.liveranking_simpleDonuts_view,
        name='liveranking_simpleDonuts',
    ),
    path(
        'liveranking/', views.liveranking_auto_view, name='liveranking_auto_no_round'
    ),
    path(
        'liveranking/simple/',
        views.liveranking_simple_view,
        name='liveranking_simple_no_round',
    ),
    path(
        'liveranking/auto_donuts/',
        views.liveranking_autoDonuts_view,
        name='liveranking_autoDonuts_no_round',
    ),
    path(
        'liveranking/simple_donuts/',
        views.liveranking_simpleDonuts_view,
        name='liveranking_simpleDonuts_no_round',
    ),
]
