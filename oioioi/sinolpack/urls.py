from django.conf.urls import url

from oioioi.sinolpack import views

app_name = 'sinolpack'

urlpatterns = [
    url(
        r'^sinolpack/extra/(?P<file_id>\d+)/$',
        views.download_extra_file_view,
        name='download_extra_file',
    ),
]
