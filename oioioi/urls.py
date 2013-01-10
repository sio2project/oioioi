from django.conf import settings
from django.conf.urls import patterns, include, url
from django.utils.importlib import import_module
from django.contrib import admin as django_admin
import oioioi.base.registration_backend
from oioioi.base import admin

django_admin.autodiscover()

handler500 = 'oioioi.base.views.handler500'

urlpatterns = []

for app in settings.INSTALLED_APPS:
    if app.startswith('oioioi.'):
        try:
            urls_module = import_module(app + '.urls')
            urlpatterns += getattr(urls_module, 'urlpatterns')
        except ImportError:
            pass

urlpatterns.extend([
#    url(r'^admin/doc/', include('django.contrib.admindocs.urls')),
    url(r'^admin/', include(admin.site.urls)),
    url(r'^grappelli/', include('grappelli.urls')),

    url(r'^file/(?P<filename>.*)$',
        'oioioi.filetracker.views.raw_file_view'),
])

urlpatterns += oioioi.base.registration_backend.urlpatterns
