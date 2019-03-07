from django.conf.urls import url

from oioioi.rankings import views

app_name = 'rankings'

contest_patterns = [
    url(r'^ranking/$', views.ranking_view, name='default_ranking'),
    url(r'^ranking/get_users_in_ranking/$', views.get_users_in_ranking_view,
            name='get_users_in_ranking'),
    url(r'^ranking/(?P<key>[a-z0-9_-]+)/$', views.ranking_view,
        name='ranking'),
    url(r'^ranking/(?P<key>[a-z0-9_-]+)/csv/$', views.ranking_csv_view,
            name='ranking_csv'),
    url(r'^ranking/(?P<key>[a-z0-9_-]+)/invalidate/$',
            views.ranking_invalidate_view, name='ranking_invalidate'),
]
