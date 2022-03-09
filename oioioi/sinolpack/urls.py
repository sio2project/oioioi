from django.urls import re_path

from oioioi.sinolpack import views

app_name = 'sinolpack'

urlpatterns = [
    re_path(
        r'^sinolpack/extra/(?P<file_id>\d+)/$',
        views.download_extra_file_view,
        name='download_extra_file',
    ),
]
