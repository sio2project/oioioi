from django.urls import include, re_path

from oioioi.forum import views

app_name = 'forum'

forum_patterns = [
    re_path(r'^$', views.forum_view, name='forum'),
    re_path(r'^lock/$', views.lock_forum_view, name='forum_lock'),
    re_path(r'^unlock/$', views.unlock_forum_view, name='forum_unlock'),
    re_path(r'^latest_posts/$', views.latest_posts_forum_view, name='forum_latest_posts'),
    re_path(r'^(?P<category_id>\d+)/$', views.category_view, name='forum_category'),
    re_path(
        r'^(?P<category_id>\d+)/delete/$',
        views.delete_category_view,
        name='forum_category_delete',
    ),
    re_path(
        r'^(?P<category_id>\d+)/toggle_reactions/$',
        views.toggle_reactions_in_category,
        name='forum_category_toggle_reactions',
    ),
    re_path(
        r'^(?P<category_id>\d+)/move_up/$',
        views.move_up_category_view,
        name='forum_category_move_up',
    ),
    re_path(
        r'^(?P<category_id>\d+)/move_down/$',
        views.move_down_category_view,
        name='forum_category_move_down',
    ),
    re_path(
        r'^(?P<category_id>\d+)/(?P<thread_id>\d+)/$',
        views.thread_view,
        name='forum_thread',
    ),
    re_path(
        r'^(?P<category_id>\d+)/(?P<thread_id>\d+)/delete/$',
        views.delete_thread_view,
        name='forum_thread_delete',
    ),
    re_path(
        r'^(?P<category_id>\d+)/add_thread/$',
        views.thread_add_view,
        name='forum_add_thread',
    ),
    re_path(
        r'^(?P<category_id>\d+)/(?P<thread_id>\d+)/(?P<post_id>\d+)/edit/$',
        views.edit_post_view,
        name='forum_post_edit',
    ),
    re_path(
        r'^(?P<category_id>\d+)/(?P<thread_id>\d+)/(?P<post_id>\d+)/delete/$',
        views.delete_post_view,
        name='forum_post_delete',
    ),
    re_path(
        r'^(?P<category_id>\d+)/(?P<thread_id>\d+)/(?P<post_id>\d+)/report/$',
        views.report_post_view,
        name='forum_post_report',
    ),
    re_path(
        r'^(?P<category_id>\d+)/(?P<thread_id>\d+)/(?P<post_id>\d+)/approve/' r'$',
        views.approve_post_view,
        name='forum_post_approve',
    ),
    re_path(
        r'^(?P<category_id>\d+)/(?P<thread_id>\d+)/(?P<post_id>\d+)'
        r'/revoke_approval/$',
        views.revoke_approval_post_view,
        name='forum_post_revoke_approval',
    ),
    re_path(
        r'^(?P<category_id>\d+)/(?P<thread_id>\d+)/(?P<post_id>\d+)/hide/$',
        views.hide_post_view,
        name='forum_post_hide',
    ),
    re_path(
        r'^(?P<category_id>\d+)/(?P<thread_id>\d+)/(?P<post_id>\d+)/$',
        views.show_post_view,
        name='forum_post_show',
    ),
    re_path(
        r'^(?P<category_id>\d+)/(?P<thread_id>\d+)/(?P<post_id>\d+)/toggle_reaction/$',
        views.post_toggle_reaction,
        name='forum_post_toggle_reaction',
    ),
    re_path(r'^user/(?P<user_id>\d+)/ban/$', views.ban_user_view, name='forum_user_ban'),
    re_path(
        r'^edit_message/$',
        views.edit_message_view,
        name='edit_forum_message',
    ),
    re_path(
        r'^edit_new_post_message/$',
        views.edit_new_post_message_view,
        name='edit_forum_new_post_message',
    ),
]

contest_patterns = [
    re_path(r'^forum/', include(forum_patterns)),
]
