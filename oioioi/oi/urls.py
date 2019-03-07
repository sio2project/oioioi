from django.conf.urls import url

from oioioi.oi import views

app_name = 'oi'

urlpatterns = [
    url(r'^oi/cities/$', views.cities_view),
    url(r'^oi/schools/$', views.schools_view),
    url(r'^oi/schools/similar/$', views.schools_similar_view,
        name='schools_similar'),
    url(r'^oi/schools/add/$', views.add_school_view, name='add_school'),
    url(r'^oi/schools/choose/(?P<school_id>[0-9]+)/$',
        views.choose_school_view, name='choose_school'),
]
