from importlib import import_module

from django.conf import settings
from django.contrib import admin as django_admin
from django.urls import include, re_path
from django.views import i18n

from oioioi.base import registration_backend
from oioioi.filetracker.views import raw_file_view

django_admin.autodiscover()

handler403 = 'oioioi.base.views.handler403'
handler404 = 'oioioi.base.views.handler404'
handler500 = 'oioioi.base.views.handler500'

urlpatterns = [
    re_path(
        r'^jsi18n/$',
        i18n.JavaScriptCatalog.as_view(
            packages=[
                'oioioi._locale',
            ]
        ),
        name='javascript_catalog',
    ),
    re_path(r'^nested_admin/', include('nested_admin.urls')),
    re_path(r'^captcha/', include('captcha.urls')),
]

if settings.DEBUG:
    import debug_toolbar

    urlpatterns += [
        re_path(r'^__debug__/', include(debug_toolbar.urls)),
    ]

for app in settings.INSTALLED_APPS:
    if app.startswith('oioioi.'):
        try:
            # Django imports views lazily, and since there are some decorators
            # that have to run, all views need to be imported at startup
            import_module(app + '.views')
            urls_module = import_module(app + '.urls')
            if hasattr(urls_module, 'urlpatterns'):
                urlpatterns += getattr(urls_module, 'urlpatterns')
        except ImportError:
            pass

urlpatterns.extend(
    [
        re_path(r'^file/(?P<filename>.*)/$', raw_file_view, name='raw_file'),
    ]
)

urlpatterns += registration_backend.urlpatterns
