from django.urls import path

from oioioi.sinolpack import views

app_name = 'sinolpack'

urlpatterns = [
    path(
        'sinolpack/extra/<int:file_id>/',
        views.download_extra_file_view,
        name='download_extra_file',
    ),
]
