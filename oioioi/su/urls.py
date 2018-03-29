from django.conf.urls import url

from oioioi.su import views

urlpatterns = [
    url(r'^su/$', views.su_view, name='su'),
    url(r'^get_suable_usernames/', views.get_suable_users_view,
            name='get_suable_users'),
    url(r'^su_reset/$', views.su_reset_view, name='su_reset'),
]
