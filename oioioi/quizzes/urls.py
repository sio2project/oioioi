from django.conf.urls import url

from oioioi.quizzes import views

app_name = 'quizzes'

urlpatterns = [
    url(
        r'^quizpicture/(?P<mode>[qa])/(?P<picture_id>\d+)/$',
        views.picture_view,
        name='picture_view',
    ),
]
