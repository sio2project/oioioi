from django.urls import path, re_path

from oioioi.oi import views

app_name = 'oi'

urlpatterns = [
    path('oi/cities/', views.cities_view),
    path('oi/schools/', views.schools_view),
    path('oi/schools/similar/', views.schools_similar_view, name='schools_similar'),
    path('oi/schools/add/', views.add_school_view, name='add_school'),
    path(
        'oi/schools/choose/<int:school_id>/',
        views.choose_school_view,
        name='choose_school',
    ),
    re_path(
        r'^oi/consent/(?P<participant_id>[0-9]+)/$',
        views.consent_view,
        name='view_consent',
    ),
]

contest_patterns = [
    re_path(r'^register/oicities/$', views.cities_view),
    re_path(r'^register/oischools/$', views.schools_view),
]
