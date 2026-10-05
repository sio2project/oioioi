from django.urls import re_path

from oioioi.quizzes import views

app_name = "quizzes"

urlpatterns = [
    re_path(
        r"^quizpicture/(?P<mode>[qa])/(?P<picture_id>\d+)/$",
        views.picture_view,
        name="picture_view",
    ),
]
