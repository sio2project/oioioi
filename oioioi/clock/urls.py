from django.conf.urls import patterns, url
from django.core.urlresolvers import reverse_lazy

urlpatterns = patterns('',
    url(r'^$', 'oioioi.clock.views.get_time_view'),
)
