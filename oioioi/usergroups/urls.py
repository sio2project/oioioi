from django.urls import path
from django.urls import re_path

from oioioi.usergroups import views

app_name = 'usergroups'

urlpatterns = [
    path(
        'usergroups/list/',
        views.GroupsListView.as_view(),
        name='teacher_usergroups_list',
    ),
    path(
        'usergroups/add/',
        views.GroupsAddView.as_view(),
        name='teacher_usergroups_add_group',
    ),
    path(
        'usergroups/show/<int:usergroup_id>/',
        views.GroupsDetailView.as_view(),
        name='teacher_usergroup_detail',
    ),
    path(
        'usergroups/addition/off/<int:usergroup_id>/',
        views.set_addition_view,
        {'value': False},
        name='usergroups_disable_addition',
    ),
    path(
        'usergroups/addition/on/<int:usergroup_id>/',
        views.set_addition_view,
        {'value': True},
        name='usergroups_enable_addition',
    ),
    path(
        'usergroups/addition/key/regenerate/<int:usergroup_id>/',
        views.regenerate_addition_key_view,
        name='usergroups_regenerate_addition_key',
    ),
    path(
        'usergroups/<int:usergroup_id>/members/delete/',
        views.delete_members_view,
        name='usergroups_delete_members',
    ),
    path(
        'usergroups/delete/<int:usergroup_id>/',
        views.GroupsDeleteView.as_view(),
        name='delete_usergroup_confirmation',
    ),
    path(
        'usergroups/sharing/on/<int:usergroup_id>/',
        views.set_sharing_view,
        {'value': True},
        name='usergroups_enable_sharing',
    ),
    path(
        'usergroups/sharing/off/<int:usergroup_id>/',
        views.set_sharing_view,
        {'value': False},
        name='usergroups_disable_sharing',
    ),
    path(
        'usergroups/sharing/key/regenerate/<int:usergroup_id>/',
        views.regenerate_sharing_key_view,
        name='usergroups_regenerate_sharing_key',
    ),
    path(
        'usergroups/<int:usergroup_id>/owners/delete/',
        views.delete_owners_view,
        name='usergroups_delete_owners',
    ),
    path(
        'usergroups/attach/',
        views.attach_to_contest_view,
        name='usergroup_attach_to_contest',
    ),
    path(
        'usergroups/<int:usergroup_id>/detach/',
        views.detach_from_contest_view,
        name='usergroup_detach_from_contest',
    ),
]

noncontest_patterns = [
    re_path(
        r'^usergroups/join/(?P<key>[0-9a-zA-Z-_=]+)/$',
        views.join_usergroup_view,
        name='usergroups_user_join',
    ),
    re_path(
        r'^usergroups/share/(?P<key>[0-9a-zA-Z-_=]+)/$',
        views.become_owner_view,
        name='usergroups_become_owner',
    ),
]
