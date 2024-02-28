from django.conf import settings
from django.urls import include, re_path

from oioioi.teachers import views

app_name = 'teachers'

member_type_dependent_patterns = [
    re_path(r'^show/$', views.members_view, name='show_members'),
    re_path(
        r'^registration/on/$',
        views.set_registration_view,
        {'value': True},
        name='teachers_enable_registration',
    ),
    re_path(
        r'^registration/off/$',
        views.set_registration_view,
        {'value': False},
        name='teachers_disable_registration',
    ),
    re_path(
        r'^registration/regen/$',
        views.regenerate_key_view,
        name='teachers_regenerate_key',
    ),
    re_path(r'^delete/$', views.delete_members_view, name='teachers_delete_members'),

    re_path(
        r'^registration/add_user/$',
        views.add_user_to_contest,
        name='teachers_add_user_to_contest'),
    re_path(
        r'^registration/get_appendable_users/$',
        views.get_appendable_users_view,
        name='teachers_get_appendable_users'),
]

contest_patterns = [
    re_path(
        r'^teachers/(?P<member_type>pupil|teacher)/',
        include(member_type_dependent_patterns),
    ),
    re_path(
        r'^join/(?P<key>[0-9a-zA-Z-_=]+)/$',
        views.activate_view,
        name='teachers_activate_member',
    ),
    re_path(
        r'^teachers/members/import/(?P<other_contest_id>[a-z0-9_-]+)/$',
        views.bulk_add_members_view,
        name='teachers_bulk_add_members',
    ),
]

urlpatterns = [
    re_path(r'^teachers/add/$', views.add_teacher_view, name='add_teacher'),
    re_path(
        r'^teachers/accept/(?P<user_id>\d+)/$',
        views.accept_teacher_view,
        name='accept_teacher',
    ),
    re_path(r'^user-search/$', views.get_non_teacher_names, name='user_search'),
]

if 'oioioi.simpleui' in settings.INSTALLED_APPS:
    noncontest_patterns = [
        re_path(
            r'^teacher-dashboard/$',
            views.teacher_dashboard_view,
            name='teacher_dashboard',
        ),
    ]

    contest_patterns += [
        re_path(
            r'^teacher-contest/dashboard/$',
            views.contest_dashboard_view,
            name='teacher_contest_dashboard',
        ),
        re_path(
            r'^teacher-contest/dashboard/(?P<round_pk>[0-9]+)/$',
            views.contest_dashboard_view,
            name='teacher_contest_dashboard',
        ),
    ]
