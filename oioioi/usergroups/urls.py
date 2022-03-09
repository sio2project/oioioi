from django.urls import re_path

from oioioi.usergroups import views

app_name = 'usergroups'

urlpatterns = [
    re_path(
        r'^usergroups/list/$',
        views.GroupsListView.as_view(),
        name='teacher_usergroups_list',
    ),
    re_path(
        r'^usergroups/add/$',
        views.GroupsAddView.as_view(),
        name='teacher_usergroups_add_group',
    ),
    re_path(
        r'^usergroups/show/(?P<usergroup_id>\d+)/$',
        views.GroupsDetailView.as_view(),
        name='teacher_usergroup_detail',
    ),
    re_path(
        r'^usergroups/addition/off/(?P<usergroup_id>\d+)/$',
        views.set_addition_view,
        {'value': False},
        name='usergroups_disable_addition',
    ),
    re_path(
        r'^usergroups/addition/on/(?P<usergroup_id>\d+)/$',
        views.set_addition_view,
        {'value': True},
        name='usergroups_enable_addition',
    ),
    re_path(
        r'^usergroups/addition/key/regenerate/(?P<usergroup_id>\d+)/$',
        views.regenerate_addition_key_view,
        name='usergroups_regenerate_addition_key',
    ),
    re_path(
        r'^usergroups/(?P<usergroup_id>\d+)/members/delete/$',
        views.delete_members_view,
        name='usergroups_delete_members',
    ),
    re_path(
        r'^usergroups/delete/(?P<usergroup_id>\d+)/$',
        views.GroupsDeleteView.as_view(),
        name='delete_usergroup_confirmation',
    ),
    re_path(
        r'^usergroups/sharing/on/(?P<usergroup_id>\d+)/$',
        views.set_sharing_view,
        {'value': True},
        name='usergroups_enable_sharing',
    ),
    re_path(
        r'^usergroups/sharing/off/(?P<usergroup_id>\d+)/$',
        views.set_sharing_view,
        {'value': False},
        name='usergroups_disable_sharing',
    ),
    re_path(
        r'^usergroups/sharing/key/regenerate/(?P<usergroup_id>\d+)/$',
        views.regenerate_sharing_key_view,
        name='usergroups_regenerate_sharing_key',
    ),
    re_path(
        r'^usergroups/(?P<usergroup_id>\d+)/owners/delete/$',
        views.delete_owners_view,
        name='usergroups_delete_owners',
    ),
    re_path(
        r'^usergroups/attach/$',
        views.attach_to_contest_view,
        name='usergroup_attach_to_contest',
    ),
    re_path(
        r'^usergroups/(?P<usergroup_id>\d+)/detach/$',
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
