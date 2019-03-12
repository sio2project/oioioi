from django.conf.urls import include, url

from oioioi import urls
from oioioi.contests.urls import make_patterns

contest_patterns = [
    url(r'^render_contest_id/$',
        'oioioi.contests.tests.tests.render_contest_id_view'),
]

namespaced_patterns = [
    url(r'^namespaced_id/$',
        'oioioi.contests.tests.tests.print_contest_id_view',
        name='print_contest_id'),
]

neutral_patterns = [
    url(r'^id/$', 'oioioi.contests.tests.tests.print_contest_id_view',
        name='print_contest_id'),
    url(r'', include((namespaced_patterns, 'namespace'))),
]


noncontest_patterns = [
    url(r'noncontest_id/$',
        'oioioi.contests.tests.tests.print_contest_id_view',
        name='noncontest_print_contest_id'),
]

urlpatterns = make_patterns(neutral_patterns, contest_patterns,
        noncontest_patterns, urls.urlpatterns)
