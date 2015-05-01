from django.conf.urls import patterns, include, url

contest_patterns = patterns('oioioi.rankings.views',
    url(r'^ranking/$', 'ranking_view', name='default_ranking'),
    url(r'^ranking/get_users_in_ranking/$', 'get_users_in_ranking_view',
            name='get_users_in_ranking'),
    url(r'^ranking/(?P<key>[a-z0-9_-]+)/$', 'ranking_view', name='ranking'),
    url(r'^ranking/(?P<key>[a-z0-9_-]+)/csv/$', 'ranking_csv_view',
            name='ranking_csv'),
)
