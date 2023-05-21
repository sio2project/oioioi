from django.urls import re_path

from oioioi.newsfeed import views

app_name = 'newsfeed'

urlpatterns = [
    re_path(r'^news/add/$', views.add_news_view, name='add_news'),
    re_path(
        r'^news/delete/(?P<news_id>\d+)/$', views.delete_news_view, name='delete_news'
    ),
    re_path(r'^news/edit/(?P<news_id>\d+)/$', views.edit_news_view, name='edit_news'),
    re_path(r'^news/newsfeed/$', views.newsfeed_view, name='newsfeed'),
]
