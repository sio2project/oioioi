from django.urls import re_path

from oioioi.oi import views

app_name = 'oi'

urlpatterns = [
    re_path(r'^oi/cities/$', views.cities_view),
    re_path(r'^oi/schools/$', views.schools_view),
    re_path(
        r'^oi/schools/similar/$', views.schools_similar_view, name='schools_similar'
    ),
    re_path(r'^oi/schools/add/$', views.add_school_view, name='add_school'),
    re_path(
        r'^oi/schools/choose/(?P<school_id>[0-9]+)/$',
        views.choose_school_view,
        name='choose_school',
    ),
]
