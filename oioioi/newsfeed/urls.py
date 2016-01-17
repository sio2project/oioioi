from django.conf.urls import patterns, url
from oioioi.newsfeed import views


urlpatterns = patterns('oioioi.newsfeed.views',
    url(r'^news/add/$', views.add_news_view,
        name='add_news'),
    url(r'^news/delete/(?P<news_id>\d+)/$', views.delete_news_view,
        name='delete_news'),
    url(r'^news/edit/(?P<news_id>\d+)/$', views.edit_news_view,
        name='edit_news'),
    url(r'^news/newsfeed/$', views.newsfeed_view,
        name='newsfeed'),
)
