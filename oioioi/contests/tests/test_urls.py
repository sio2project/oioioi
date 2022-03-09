from django.urls import include, re_path

from oioioi import urls
from oioioi.contests.tests import tests
from oioioi.contests.urls import make_patterns

contest_patterns = [
    re_path(
        r'^render_contest_id/$', tests.render_contest_id_view, name='render_contest_id'
    ),
]

namespaced_patterns = [
    re_path(r'^namespaced_id/$', tests.print_contest_id_view, name='print_contest_id'),
]

neutral_patterns = [
    re_path(r'^id/$', tests.print_contest_id_view, name='print_contest_id'),
    re_path(r'', include((namespaced_patterns, 'namespace'))),
]


noncontest_patterns = [
    re_path(
        r'noncontest_id/$',
        tests.print_contest_id_view,
        name='noncontest_print_contest_id',
    ),
]

urlpatterns = make_patterns(
    neutral_patterns, contest_patterns, noncontest_patterns, urls.urlpatterns
)
