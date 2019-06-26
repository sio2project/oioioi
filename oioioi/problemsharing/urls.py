from django.conf.urls import url

from oioioi.problemsharing import views

app_name = "problemsharing"

urlpatterns = [
    url(r'^friends/$', views.FriendshipsView.as_view(),
        name='problemsharing_friends'),
    url(r'^friends/hints/$', views.friend_hints_view,
        name='problemsharing_friend_hints')
]
