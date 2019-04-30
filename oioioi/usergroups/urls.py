from django.conf.urls import url

from oioioi.usergroups import views

app_name = 'usergroups'

urlpatterns = [
    url(r'^usergroups/list/$', views.GroupsListView.as_view(),
        name='teacher_usergroups_list'),
    url(r'^usergroups/add/$', views.GroupsAddView.as_view(),
        name='teacher_usergroups_add_group'),
    url(r'^usergroups/show/(?P<usergroup_id>\d+)/$',
        views.GroupsDetailView.as_view(), name='teacher_usergroup_detail'),
    url(r'^usergroups/addition/off/(?P<usergroup_id>\d+)/$', views.set_addition_view,
        {'value': False}, name='usergroups_disable_addition'),
    url(r'^usergroups/addition/on/(?P<usergroup_id>\d+)/$', views.set_addition_view,
        {'value': True}, name='usergroups_enable_addition'),
    url(r'^usergroups/addition/key/regenerate/(?P<usergroup_id>\d+)/$',
        views.regenerate_addition_key_view, name='usergroups_regenerate_addition_key'),
    url(r'^usergroups/(?P<usergroup_id>\d+)/members/delete/$', views.delete_members_view,
        name='usergroups_delete_members'),
    url(r'^usergroups/delete/(?P<usergroup_id>\d+)/$', views.GroupsDeleteView.as_view(),
        name='delete_usergroup_confirmation'),
    url(r'^usergroups/sharing/on/(?P<usergroup_id>\d+)/$', views.set_sharing_view,
        {'value': True}, name='usergroups_enable_sharing'),
    url(r'^usergroups/sharing/off/(?P<usergroup_id>\d+)/$', views.set_sharing_view,
        {'value': False}, name='usergroups_disable_sharing'),
    url(r'^usergroups/sharing/key/regenerate/(?P<usergroup_id>\d+)/$',
        views.regenerate_sharing_key_view, name='usergroups_regenerate_sharing_key'),
    url(r'^usergroups/(?P<usergroup_id>\d+)/owners/delete/$', views.delete_owners_view,
        name='usergroups_delete_owners')
]

noncontest_patterns = [
    url(r'^usergroups/join/(?P<key>[0-9a-zA-Z-_=]+)/$', views.join_usergroup_view,
            name='usergroups_user_join'),
    url(r'^usergroups/share/(?P<key>[0-9a-zA-Z-_=]+)/$', views.become_owner_view,
            name='usergroups_become_owner'),
]