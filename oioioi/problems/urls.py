from django.conf.urls import patterns, include, url

contest_patterns = patterns('oioioi.problems.views',
    url(r'^problems/add$', 'add_or_update_problem_view',
        name='add_or_update_contest_problem'),
)

urlpatterns = patterns('oioioi.problems.views',
    url(r'^statement/(?P<statement_id>\d+)$', 'show_statement_view',
        name='show_statement'),
    url(r'^problems/add$', 'add_or_update_problem_view',
        name='add_or_update_problem'),
    url(r'^c/(?P<contest_id>[a-z0-9_-]+)/', include(contest_patterns)),
)
