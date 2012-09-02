from django.conf.urls import patterns, include, url

contest_patterns = patterns('oioioi.teachers.views',
    url(r'^teachers/participants/$', 'participants_view',
        name='teachers_participants'),
    url(r'^join/(?P<key>[0-9a-f]{40})$', 'activate_participant_view',
        name='teachers_activate_participant'),
    url(r'^teachers/registration/on$', 'set_registration_view',
        {'value': True}, name='teachers_enable_registration'),
    url(r'^teachers/registration/off$', 'set_registration_view',
        {'value': False}, name='teachers_disable_registration'),
    url(r'^teachers/registration/regen$', 'regenerate_key_view',
        name='teachers_regenerate_key'),
    url(r'^teachers/participants/delete$', 'delete_participants_view',
        name='teachers_delete_participants'),
    url(r'^teachers/participants/import/(?P<other_contest_id>[a-z0-9_-]+)$',
        'bulk_add_participants_view', name='teachers_bulk_add_participants'),
)

urlpatterns = patterns('oioioi.teachers.views',
    url(r'^c/(?P<contest_id>[a-z0-9_-]+)/', include(contest_patterns)),
    url(r'^teachers/add$', 'add_teacher_view', name='add_teacher'),
    url(r'^teachers/accept/(?P<user_id>\d+)$', 'accept_teacher_view',
        name='accept_teacher'),
)
