from django.conf.urls import patterns, url

urlpatterns = patterns('',
    url(r'^c/(?P<contest_id>\w+)/id$',
        'oioioi.contests.tests.print_contest_id_view'),
    url(r'^contest_id$',
        'oioioi.contests.tests.print_contest_id_view'),
    url(r'^render_contest_id$',
        'oioioi.contests.tests.render_contest_id_view'),
)
