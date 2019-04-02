from django.conf.urls import include, url

from oioioi import urls
from oioioi.contests.urls import make_patterns
from oioioi.contests.tests import tests

contest_patterns = [
    url(r'^render_contest_id/$', tests.render_contest_id_view,
        name='render_contest_id'),
]

namespaced_patterns = [
    url(r'^namespaced_id/$', tests.print_contest_id_view,
        name='print_contest_id'),
]

neutral_patterns = [
    url(r'^id/$', tests.print_contest_id_view,
        name='print_contest_id'),
    url(r'', include((namespaced_patterns, 'namespace'))),
]


noncontest_patterns = [
    url(r'noncontest_id/$', tests.print_contest_id_view,
        name='noncontest_print_contest_id'),
]

urlpatterns = make_patterns(neutral_patterns, contest_patterns,
                            noncontest_patterns, urls.urlpatterns)
