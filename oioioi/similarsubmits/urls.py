from django.conf.urls import url

from oioioi.similarsubmits import views

app_name = 'similarsubmits'

contest_patterns = [
    url(
        r'^(?P<entry_id>\d+)/mark_guilty/$', views.mark_guilty_view, name='mark_guilty'
    ),
    url(
        r'^(?P<entry_id>\d+)/mark_not_guilty/$',
        views.mark_not_guilty_view,
        name='mark_not_guilty',
    ),
    url(r'^bulk_add/$', views.bulk_add_similarities_view, name='bulk_add_similarities'),
]
