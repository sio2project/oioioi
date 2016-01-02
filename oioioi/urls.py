from django.conf import settings
from django.conf.urls import patterns, include, url
from django.utils.importlib import import_module
from django.contrib import admin as django_admin

from oioioi.base import registration_backend

django_admin.autodiscover()

handler403 = 'oioioi.base.views.handler403'
handler404 = 'oioioi.base.views.handler404'
handler500 = 'oioioi.base.views.handler500'

js_info_dict = {
    'packages': ('oioioi',),
}

urlpatterns = patterns('',
    (r'^jsi18n/$', 'django.views.i18n.javascript_catalog', js_info_dict),
)

for app in settings.INSTALLED_APPS:
    if app.startswith('oioioi.'):
        try:
            # Django imports views lazily, and sice there are some decorators
            # that have to run, all views need to be imported at startup
            import_module(app + '.views')
            urls_module = import_module(app + '.urls')
            if hasattr(urls_module, 'urlpatterns'):
                urlpatterns += getattr(urls_module, 'urlpatterns')
        except ImportError:
            pass

urlpatterns.extend([
    url(r'^grappelli/', include('grappelli.urls')),

    url(r'^file/(?P<filename>.*)/$',
        'oioioi.filetracker.views.raw_file_view'),
])

urlpatterns += registration_backend.urlpatterns
