from django.urls import path
from django.urls import include

from oioioi import urls
from oioioi.contests.tests import tests
from oioioi.contests.urls import make_patterns

contest_patterns = [
    path(
        'render_contest_id/', tests.render_contest_id_view, name='render_contest_id'
    ),
]

namespaced_patterns = [
    path('namespaced_id/', tests.print_contest_id_view, name='print_contest_id'),
]

neutral_patterns = [
    path('id/', tests.print_contest_id_view, name='print_contest_id'),
    path('', include((namespaced_patterns, 'namespace'))),
]


noncontest_patterns = [
    path(
        'noncontest_id/',
        tests.print_contest_id_view,
        name='noncontest_print_contest_id',
    ),
]

urlpatterns = make_patterns(
    neutral_patterns, contest_patterns, noncontest_patterns, urls.urlpatterns
)
