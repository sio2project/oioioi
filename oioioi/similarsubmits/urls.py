from django.conf.urls import patterns, include, url

contest_patterns = patterns('oioioi.similarsubmits.views',
    url(r'^(?P<entry_id>\d+)/mark_guilty/$', 'mark_guilty_view',
        name='mark_guilty'),
    url(r'^(?P<entry_id>\d+)/mark_not_guilty/$', 'mark_not_guilty_view',
        name='mark_not_guilty'),
    url(r'^bulk_add/$', 'bulk_add_similarities_view',
        name='bulk_add_similarities'),
)
