from django.conf.urls import patterns, include, url

urlpatterns = patterns('oioioi.problems.views',
    url(r'^statement/(?P<statement_id>\d+)$', 'show_statement_view'),
)
