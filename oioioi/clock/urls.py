from django.conf.urls import patterns, url
from django.core.urlresolvers import reverse_lazy

urlpatterns = patterns('',
    url(r'^round_times/$', 'oioioi.clock.views.get_times_view'),
)
