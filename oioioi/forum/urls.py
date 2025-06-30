from django.urls import path
from django.urls import include

from oioioi.forum import views

app_name = 'forum'

forum_patterns = [
    path('', views.forum_view, name='forum'),
    path('lock/', views.lock_forum_view, name='forum_lock'),
    path('unlock/', views.unlock_forum_view, name='forum_unlock'),
    path('latest_posts/', views.latest_posts_forum_view, name='forum_latest_posts'),
    path('<int:category_id>/', views.category_view, name='forum_category'),
    path(
        '<int:category_id>/delete/',
        views.delete_category_view,
        name='forum_category_delete',
    ),
    path(
        '<int:category_id>/toggle_reactions/',
        views.toggle_reactions_in_category,
        name='forum_category_toggle_reactions',
    ),
    path(
        '<int:category_id>/move_up/',
        views.move_up_category_view,
        name='forum_category_move_up',
    ),
    path(
        '<int:category_id>/move_down/',
        views.move_down_category_view,
        name='forum_category_move_down',
    ),
    path(
        '<int:category_id>/<int:thread_id>/',
        views.thread_view,
        name='forum_thread',
    ),
    path(
        '<int:category_id>/<int:thread_id>/delete/',
        views.delete_thread_view,
        name='forum_thread_delete',
    ),
    path(
        '<int:category_id>/add_thread/',
        views.thread_add_view,
        name='forum_add_thread',
    ),
    path(
        '<int:category_id>/<int:thread_id>/<int:post_id>/edit/',
        views.edit_post_view,
        name='forum_post_edit',
    ),
    path(
        '<int:category_id>/<int:thread_id>/<int:post_id>/delete/',
        views.delete_post_view,
        name='forum_post_delete',
    ),
    path(
        '<int:category_id>/<int:thread_id>/<int:post_id>/report/',
        views.report_post_view,
        name='forum_post_report',
    ),
    path(
        '<int:category_id>/<int:thread_id>/<int:post_id>/approve/',
        views.approve_post_view,
        name='forum_post_approve',
    ),
    path(
        '<int:category_id>/<int:thread_id>/<int:post_id>/revoke_approval/',
        views.revoke_approval_post_view,
        name='forum_post_revoke_approval',
    ),
    path(
        '<int:category_id>/<int:thread_id>/<int:post_id>/hide/',
        views.hide_post_view,
        name='forum_post_hide',
    ),
    path(
        '<int:category_id>/<int:thread_id>/<int:post_id>/',
        views.show_post_view,
        name='forum_post_show',
    ),
    path(
        '<int:category_id>/<int:thread_id>/<int:post_id>/toggle_reaction/',
        views.post_toggle_reaction,
        name='forum_post_toggle_reaction',
    ),
    path('user/<int:user_id>/ban/', views.ban_user_view, name='forum_user_ban'),
    path(
        'edit_message/',
        views.edit_message_view,
        name='edit_forum_message',
    ),
    path(
        'edit_new_post_message/',
        views.edit_new_post_message_view,
        name='edit_forum_new_post_message',
    ),
]

contest_patterns = [
    path('forum/', include(forum_patterns)),
]
