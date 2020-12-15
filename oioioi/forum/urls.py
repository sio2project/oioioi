from django.conf.urls import include, url

from oioioi.forum import views

app_name = 'forum'

forum_patterns = [
    url(r'^$',
        views.forum_view, name='forum'),
    url(r'^lock/$',
        views.lock_forum_view, name='forum_lock'),
    url(r'^unlock/$',
        views.unlock_forum_view, name='forum_unlock'),
    url(r'^latest_posts/$',
        views.latest_posts_forum_view, name='forum_latest_posts'),
    url(r'^(?P<category_id>\d+)/$',
        views.category_view, name='forum_category'),
    url(r'^(?P<category_id>\d+)/delete/$',
        views.delete_category_view, name='forum_category_delete'),
    url(r'^(?P<category_id>\d+)/move_up/$',
        views.move_up_category_view, name='forum_category_move_up'),
    url(r'^(?P<category_id>\d+)/move_down/$',
        views.move_down_category_view, name='forum_category_move_down'),
    url(r'^(?P<category_id>\d+)/(?P<thread_id>\d+)/$',
        views.thread_view, name='forum_thread'),
    url(r'^(?P<category_id>\d+)/(?P<thread_id>\d+)/delete/$',
        views.delete_thread_view, name='forum_thread_delete'),
    url(r'^(?P<category_id>\d+)/add_thread/$',
        views.thread_add_view, name='forum_add_thread'),
    url(r'^(?P<category_id>\d+)/(?P<thread_id>\d+)/(?P<post_id>\d+)/edit/$',
        views.edit_post_view, name='forum_post_edit'),
    url(r'^(?P<category_id>\d+)/(?P<thread_id>\d+)/(?P<post_id>\d+)/delete/$',
        views.delete_post_view, name='forum_post_delete'),
    url(r'^(?P<category_id>\d+)/(?P<thread_id>\d+)/(?P<post_id>\d+)/report/$',
        views.report_post_view, name='forum_post_report'),
    url(r'^(?P<category_id>\d+)/(?P<thread_id>\d+)/(?P<post_id>\d+)/approve/'
        r'$',
        views.approve_post_view, name='forum_post_approve'),
    url(r'^(?P<category_id>\d+)/(?P<thread_id>\d+)/(?P<post_id>\d+)'
        r'/revoke_approval/$',
        views.revoke_approval_post_view, name='forum_post_revoke_approval'),
    url(r'^(?P<category_id>\d+)/(?P<thread_id>\d+)/(?P<post_id>\d+)/hide/$',
        views.hide_post_view, name='forum_post_hide'),
    url(r'^(?P<category_id>\d+)/(?P<thread_id>\d+)/(?P<post_id>\d+)/$',
        views.show_post_view, name='forum_post_show'),
    url(r'^user/(?P<user_id>\d+)/ban/$',
        views.ban_user_view, name='forum_user_ban'),
]

contest_patterns = [
    url(r'^forum/', include(forum_patterns)),
]
