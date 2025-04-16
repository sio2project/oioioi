import sys
from importlib import import_module

from django.conf import settings
from django.contrib import admin as django_admin
from django.views import i18n
from django.urls import path
from django.urls import include, re_path

from oioioi.base import registration_backend
from oioioi.filetracker.views import raw_file_view

django_admin.autodiscover()

handler403 = 'oioioi.base.views.handler403'
handler404 = 'oioioi.base.views.handler404'
handler500 = 'oioioi.base.views.handler500'

urlpatterns = [
    path(
        'jsi18n/',
        i18n.JavaScriptCatalog.as_view(
            packages=[
                'oioioi._locale',
            ]
        ),
        name='javascript_catalog',
    ),
    path('nested_admin/', include('nested_admin.urls')),
    path('captcha/', include('captcha.urls')),
]

if settings.DEBUG:
    import debug_toolbar

    urlpatterns += [
        path('__debug__/', include(debug_toolbar.urls)),
    ]

def try_to_import_module(name):
    try:
        return import_module(name)
    except ModuleNotFoundError:
        pass
    except ImportError as e:
        if settings.DEBUG:
            print(e, file=sys.stderr)
    return None

for app in settings.INSTALLED_APPS:
    if app.startswith('oioioi.'):
        # Django imports views lazily, and since there are some decorators
        # that have to run, all views need to be imported at startup.
        try_to_import_module(app + '.views')
        # Controllers should be imported at startup, because they register
        # mixins.
        try_to_import_module(app + '.controllers')
        urls_module = try_to_import_module(app + '.urls')
        if hasattr(urls_module, 'urlpatterns'):
            urlpatterns += getattr(urls_module, 'urlpatterns')

urlpatterns.extend(
    [
        re_path(r'^file/(?P<filename>.*)/$', raw_file_view, name='raw_file'),
    ]
)

urlpatterns += registration_backend.urlpatterns
