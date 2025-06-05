from django.urls import path

from oioioi.newsfeed import views

app_name = 'newsfeed'

urlpatterns = [
    path('news/add/', views.add_news_view, name='add_news'),
    path('news/delete/<int:news_id>/', views.delete_news_view, name='delete_news'),
    path('news/edit/<int:news_id>/', views.edit_news_view, name='edit_news'),
    path('news/newsfeed/', views.newsfeed_view, name='newsfeed'),
]
