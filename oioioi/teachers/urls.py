from django.conf import settings
from django.conf.urls import include, url

from oioioi.teachers import views

app_name = 'teachers'

member_type_dependent_patterns = [
    url(r'^show/$', views.members_view, name='show_members'),
    url(r'^registration/on/$', views.set_registration_view,
        {'value': True}, name='teachers_enable_registration'),
    url(r'^registration/off/$', views.set_registration_view,
        {'value': False}, name='teachers_disable_registration'),
    url(r'^registration/regen/$', views.regenerate_key_view,
        name='teachers_regenerate_key'),
    url(r'^delete/$', views.delete_members_view,
        name='teachers_delete_members'),
]

contest_patterns = [
    url(r'^teachers/(?P<member_type>pupil|teacher)/',
        include(member_type_dependent_patterns)),
    url(r'^join/(?P<key>[0-9a-zA-Z-_=]+)/$', views.activate_view,
        name='teachers_activate_member'),
    url(r'^teachers/members/import/(?P<other_contest_id>[a-z0-9_-]+)/$',
        views.bulk_add_members_view, name='teachers_bulk_add_members'),
]

urlpatterns = [
    url(r'^teachers/add/$', views.add_teacher_view, name='add_teacher'),
    url(r'^teachers/accept/(?P<user_id>\d+)/$', views.accept_teacher_view,
        name='accept_teacher'),
]

if 'oioioi.simpleui' in settings.INSTALLED_APPS:
    noncontest_patterns = [
        url(r'^teacher-dashboard/$', views.teacher_dashboard_view,
            name='teacher_dashboard'),
    ]

    contest_patterns += [
        url(r'^teacher-contest/dashboard/$', views.contest_dashboard_view,
            name='teacher_contest_dashboard'),
        url(r'^teacher-contest/dashboard/(?P<round_pk>[0-9]+)/$',
            views.contest_dashboard_view, name='teacher_contest_dashboard'),
    ]
