from django.conf.urls import patterns, include, url

contest_patterns = patterns('oioioi.teachers.views',
    url(r'^teachers/pupils/$', 'pupils_view',
        name='teachers_pupils'),
    url(r'^join/(?P<key>[0-9a-f]{40})$', 'activate_pupil_view',
        name='teachers_activate_pupil'),
    url(r'^teachers/registration/on$', 'set_registration_view',
        {'value': True}, name='teachers_enable_registration'),
    url(r'^teachers/registration/off$', 'set_registration_view',
        {'value': False}, name='teachers_disable_registration'),
    url(r'^teachers/registration/regen$', 'regenerate_key_view',
        name='teachers_regenerate_key'),
    url(r'^teachers/pupils/delete$', 'delete_pupils_view',
        name='teachers_delete_pupils'),
    url(r'^teachers/pupils/import/(?P<other_contest_id>[a-z0-9_-]+)$',
        'bulk_add_pupils_view', name='teachers_bulk_add_pupils'),
)

urlpatterns = patterns('oioioi.teachers.views',
    url(r'^c/(?P<contest_id>[a-z0-9_-]+)/', include(contest_patterns)),
    url(r'^teachers/add$', 'add_teacher_view', name='add_teacher'),
    url(r'^teachers/accept/(?P<user_id>\d+)$', 'accept_teacher_view',
        name='accept_teacher'),
)
