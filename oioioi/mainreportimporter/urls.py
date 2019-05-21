from django.conf.urls import patterns, url

urlpatterns = patterns('oioioi.mainreportimporter.views',
    url('^import_report/$', 'import_report_view', name='import_report'),
    url('^import_report/success/$', 'import_report_success_view', name='import_report_success')
)
