from django.conf import settings
from django.conf.urls import patterns, include, url
from django.contrib import admin as django_admin
import oioioi.base.registration_backend
import oioioi.contests.urls
import oioioi.problems.urls
import oioioi.programs.urls
import oioioi.messages.urls
import oioioi.rankings.urls
import oioioi.dashboard.urls
from oioioi.base import admin

django_admin.autodiscover()

handler500 = 'oioioi.base.views.handler500'

urlpatterns = patterns('',
    url(r'^$', 'oioioi.base.views.index_view', name='index'),
    url(r'^force_error$', 'oioioi.base.views.force_error_view'),

#    url(r'^admin/doc/', include('django.contrib.admindocs.urls')),
    url(r'^admin/', include(admin.site.urls)),
    url(r'^grappelli/', include('grappelli.urls')),

    url(r'^clock/', include('oioioi.clock.urls')),
    url(r'^file/(?P<filename>.*)$',
        'oioioi.filetracker.views.raw_file_view'),
)

urlpatterns += oioioi.base.registration_backend.urlpatterns
urlpatterns += oioioi.contests.urls.urlpatterns
urlpatterns += oioioi.problems.urls.urlpatterns
urlpatterns += oioioi.programs.urls.urlpatterns
urlpatterns += oioioi.messages.urls.urlpatterns
urlpatterns += oioioi.rankings.urls.urlpatterns
urlpatterns += oioioi.dashboard.urls.urlpatterns

if 'oioioi.teachers' in settings.INSTALLED_APPS:
    import oioioi.teachers.urls
    urlpatterns += oioioi.teachers.urls.urlpatterns
