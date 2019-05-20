from importlib import import_module

from django.conf import settings
from django.conf.urls import include, url

from oioioi.contests import admin, views, api

app_name = 'contests'

def make_patterns(neutrals=None, contests=None, noncontests=None, globs=None):
    """Creates url patterns to be used in a custom urlconf.

       Use this function when you create a custom urlconf, for example
       when writing tests. It will allow our
       :func:`~oioioi.contests.current_contest.reverse` function
       to run correctly when using this urlconf.

       DON'T use this function when defining patterns in your app's urls.py
       file. Instead just define the following variables (though all of them
       are optional), and the file will be preprocessed by us:

        * ``contest_patterns`` - these patterns will generate urls with prefix
          ``/c/<contest_id>/`` and a request whose path matches such an url
          will have an attribute called ``contest``. For more information read
          :class:`~oioioi.contests.middleware.CurrentContestMiddleware`'s
          documentation. Use this variable if your view needs needs a contest.
        * ``urlpatterns`` - these patterns will generate urls both with
          and without the prefix. If your view doesn't depend on the contest
          or its behavior is conditional on the existence of a contest,
          you should use this variable (this should be the default choice).
        * ``noncontest_patterns`` - these patterns will generate urls without
          the prefix. Use this variable if you think that users accessing
          your views should not currently participate in any contest.

       When creating a custom urlconf, you can use this function and each
       parameter (with one exception) represents one of the mentioned
       variables:

       :param neutrals: represents ``urlpatterns``
       :param contests: represents ``contest_patterns``
       :param noncontests: represents ``noncontest_patterns``
       :param globs: represents global url patterns - those defined in
         ``oioioi.urls``. These urls won't be prefixed by us with
         ``/c/<contest_id>/``, but they could already contain urls in this
         form. When you create your custom urlconf and you want to use
         all of the existing OIOIOI urls, you can use this param to pass
         them (e.g.: ``from oioioi import urls;
         make_patterns(..., globs=urls.urlpatterns)``)

       Typically the function's return value will be assigned
       to ``urlpatterns``.
    """
    globs = globs or []

    # Django doesn't handle the situation where a pattern list contains
    # two includes with the same namespace (it acts as if all of them
    # beside the first didn't exist). If the 'globs' contains patterns
    # namespaced with 'contest' or 'noncontest', we have to extract
    # and add them to our patterns so they are taken into account.
    def glob_namespaced_patterns(namespace):
        pattern_lists = [l for l in globs
                if getattr(l, 'namespace', None) == namespace]
        return [pattern for l in pattern_lists for pattern in l.url_patterns]

    neutrals = neutrals or []
    contests = (contests or []) \
            + neutrals + glob_namespaced_patterns('contest')
    noncontests = (noncontests or []) \
            + neutrals + glob_namespaced_patterns('noncontest')

    return [
        url(r'^c/[a-z0-9_-]+/', include((contests, 'contest'))),
        url(r'', include((noncontests, 'noncontest'))),
    ] + globs


c_patterns = [
    url(r'^$', views.default_contest_view, name='default_contest_view'),
    url(r'^p/$', views.problems_list_view, name='problems_list'),
    url(r'^p/(?P<problem_instance>[a-z0-9_-]+)/$',
        views.problem_statement_view, name='problem_statement'),
    url(r'^p/(?P<problem_instance>[a-z0-9_-]+)/(?P<statement_id>\d+)/$',
        views.problem_statement_zip_index_view,
        name='problem_statement_zip_index'),
    url(r'^p/(?P<problem_instance>[a-z0-9_-]+)/(?P<statement_id>\d+)/'
         '(?P<path>.+)$',
        views.problem_statement_zip_view, name='problem_statement_zip'),
    url(r'p/(?P<problem_instance_id>[a-z0-9_-]+)/rejudge_all',
        views.rejudge_all_submissions_for_problem_view,
        name='rejudge_all_submissions_for_problem'),
    url(r'p/(?P<problem_instance_id>[a-z0-9_-]+)/reset_limits',
        views.reset_tests_limits_for_probleminstance_view,
        name='reset_tests_limits_for_probleminstance'),

    url(r'^submit/$', views.submit_view, name='submit'),
    url(r'^submit/(?P<problem_instance_id>[a-z0-9_-]+)/$', views.submit_view,
        name='submit'),
    url(r'^submissions/$', views.my_submissions_view, name='my_submissions'),
    url(r'^files/$', views.contest_files_view, name='contest_files'),
    url(r'^ca/(?P<attachment_id>\d+)/$', views.contest_attachment_view,
        name='contest_attachment'),
    url(r'^pa/(?P<attachment_id>\d+)/$', views.problem_attachment_view,
        name='problem_attachment'),
    url(r'^user_hints/$', views.contest_user_hints_view,
        name='contest_user_hints'),
    url(r'^u/(?P<user_id>\d+)$', views.user_info_view,
        name='user_info'),
    url(r'^user_info_redirect/$', views.user_info_redirect_view,
        name='user_info_redirect'),

    url(r'^admin/', admin.contest_site.urls),
]

nonc_patterns = [
    url(r'^submissions/$', views.all_submissions_view, name='all_submissions'),
]

neutral_patterns = [
    url(r'^contest/$', views.select_contest_view, name='select_contest'),

    url(r'^s/(?P<submission_id>\d+)/$', views.submission_view,
        name='submission'),
    url(r'^s/(?P<submission_id>\d+)/rejudge/$', views.rejudge_submission_view,
        name='rejudge_submission'),
    url(r'^s/(?P<submission_id>\d+)/change_kind/(?P<kind>\w+)/$',
        views.change_submission_kind_view, name='change_submission_kind'),
    url(r'^s/(?P<submission_id>\d+)/report/(?P<report_id>\d+)/$',
        views.report_view, name='report'),
    url(r'^reattach/(?P<problem_instance_id>\d+)/contest_list/'
        '((?P<full_list>full))?',
        views.reattach_problem_contest_list_view,
        name='reattach_problem_contest_list'),
    url(r'^reattach/(?P<problem_instance_id>\d+)/'
        '(?P<contest_id>[a-z0-9_-]+)/confirm',
        views.reattach_problem_confirm_view,
        name='reattach_problem_confirm'),
]

if settings.USE_API:
    nonc_patterns += [
        # the contest information is managed manually and added after api prefix
        url(r'^api/c/(?P<contest_name>[a-z0-9_-]+)/submit/(?P<problem_short_name>[a-z0-9_-]+)$',
            api.SubmitContestSolution.as_view(), name='api_contest_submit'),
        url(r'^api/problemset/submit/(?P<problem_site_key>[0-9a-zA-Z-_=]+)$',
            api.SubmitProblemsetSolution.as_view(), name='api_problemset_submit'),
    ]

for app in settings.INSTALLED_APPS:
    if app.startswith('oioioi.'):
        try:
            urls_module = import_module(app + '.urls')
            if hasattr(urls_module, 'contest_patterns'):
                c_patterns += getattr(urls_module, 'contest_patterns')
            if hasattr(urls_module, 'noncontest_patterns'):
                nonc_patterns += getattr(urls_module, 'noncontest_patterns')
            # every "normal" urlpattern becomes a neutral pattern:
            # it can be accessed either with or without the contest prefix
            # patterns defined in the global urls.py are an exception
            if hasattr(urls_module, 'urlpatterns'):
                neutral_patterns += getattr(urls_module, 'urlpatterns')
        except ImportError:
            pass

# We actually use make_patterns here, but we don't pass the globs, because
# the algorithm in oioioi.urls has yet to capture all urls, including ours.
urlpatterns = make_patterns(neutral_patterns, c_patterns, nonc_patterns)
