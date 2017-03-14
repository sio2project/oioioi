from django.conf.urls import url

from oioioi.mailsubmit import views

contest_patterns = [
    url(r'^mailsubmit/$', views.mailsubmit_view, name='mailsubmit'),
    url(r'^mailsubmit/accept/$', views.accept_mailsubmission_view,
        name='accept_mailsubmission_default'),
    url(r'^mailsubmit/accept/(?P<mailsubmission_id>\d+)/'
        r'(?P<mailsubmission_hash>[a-z0-9]+)/$',
        views.accept_mailsubmission_view,
        name='accept_mailsubmission'),
]
