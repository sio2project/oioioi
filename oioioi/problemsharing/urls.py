from django.urls import re_path

from oioioi.problemsharing import views

app_name = "problemsharing"

urlpatterns = [
    re_path(
        r'^friends/$', views.FriendshipsView.as_view(), name='problemsharing_friends'
    ),
    re_path(
        r'^friends/hints/$', views.friend_hints_view, name='problemsharing_friend_hints'
    ),
]
