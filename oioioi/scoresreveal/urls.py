from django.conf.urls import patterns, include, url

contest_patterns = patterns('oioioi.scoresreveal.views',
    url(r'^s/(?P<submission_id>\d+)/reveal$', 'score_reveal_view',
        name='submission_score_reveal'),
)

urlpatterns = patterns('oioioi.scoresreveal.views',
   url(r'^c/(?P<contest_id>[a-z0-9_-]+)/', include(contest_patterns)),
)