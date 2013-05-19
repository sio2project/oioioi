from django.conf.urls import patterns, url, include

urlpatterns = patterns('oioioi.validator.views',
    url(r'^validator/', include('output_validator.urls')),
)
