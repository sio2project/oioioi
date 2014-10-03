from django.conf.urls import patterns, include, url


member_type_dependent_patterns = patterns('oioioi.teachers.views',
    url(r'^show/$', 'members_view',
        name='show_members'),
    url(r'^registration/on/$', 'set_registration_view',
        {'value': True}, name='teachers_enable_registration'),
    url(r'^registration/off/$', 'set_registration_view',
        {'value': False}, name='teachers_disable_registration'),
    url(r'^registration/regen/$',
        'regenerate_key_view', name='teachers_regenerate_key'),
    url(r'^delete/$', 'delete_members_view',
        name='teachers_delete_members'),
)

contest_patterns = patterns('oioioi.teachers.views',
    url(r'^teachers/(?P<member_type>pupil|teacher)/',
        include(member_type_dependent_patterns)),
    url(r'^join/(?P<key>[0-9a-zA-Z-_=]+)/$', 'activate_view',
        name='teachers_activate_member'),
    # Unused in current UI implementation:
    url(r'^teachers/members/import/(?P<other_contest_id>[a-z0-9_-]+)/$',
        'bulk_add_members_view', name='teachers_bulk_add_members'),
)

urlpatterns = patterns('oioioi.teachers.views',
    url(r'^c/(?P<contest_id>[a-z0-9_-]+)/', include(contest_patterns)),
    url(r'^teachers/add/$', 'add_teacher_view', name='add_teacher'),
    url(r'^teachers/accept/(?P<user_id>\d+)/$', 'accept_teacher_view',
        name='accept_teacher'),
)
