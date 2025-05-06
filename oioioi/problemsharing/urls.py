from django.urls import path

from oioioi.problemsharing import views

app_name = "problemsharing"

urlpatterns = [
    path('friends/', views.FriendshipsView.as_view(), name='problemsharing_friends'),
    path(
        'friends/hints/', views.friend_hints_view, name='problemsharing_friend_hints'
    ),
]
