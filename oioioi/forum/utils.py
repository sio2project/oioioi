from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _

from oioioi.base.permissions import make_condition, make_request_condition
from oioioi.base.utils import request_cached
from oioioi.contests.utils import is_contest_admin
from oioioi.forum.models import Category, Post, Thread, Ban


@make_request_condition
def forum_exists(request):
    return hasattr(request.contest, 'controller') \
            and hasattr(request.contest.controller, 'create_forum') \
            and request.contest.controller.create_forum \
            and hasattr(request.contest, 'forum')


@make_request_condition
@request_cached
def forum_exists_and_visible(request):
    # checks whether the forum exists and
    # - is locked & visible
    # - is not locked
    # - user is contest admin
    return forum_exists(request) and (not
            (request.contest.forum.is_locked(request.timestamp) and
             not request.contest.forum.visible)) or (is_contest_admin(request))


@make_condition()
def is_proper_forum(request, *args, **kwargs):
    """Checks whether kwargs describe proper part of the forum,
       eg. Category(category_id) is connected with that forum and
       Thread(thread_id) belongs to that particular category"""
    if not forum_exists(request):
        return False
    forum = request.contest.forum
    if 'category_id' in kwargs:
        category = get_object_or_404(Category, id=kwargs['category_id'])
        if not category.forum == forum:
            return False
    if 'thread_id' in kwargs:
        thread = get_object_or_404(Thread, id=kwargs['thread_id'])
        if not thread.category == category:
            return False
    if 'post_id' in kwargs:
        post = get_object_or_404(Post, id=kwargs['post_id'])
        if not post.thread == thread:
            return False
    return True


@make_request_condition
def can_interact_with_users(request):
    if request.user.is_anonymous:
        return False
    is_banned = Ban.is_banned(request.contest.forum, request.user)
    is_locked = request.contest.forum.is_locked(request.timestamp)
    return is_contest_admin(request) or (not is_banned and not is_locked)


@make_request_condition
def can_interact_with_admins(request):
    if request.user.is_anonymous:
        return False
    is_banned = Ban.is_banned(request.contest.forum, request.user)
    return is_contest_admin(request) or not is_banned


def get_forum_ct(category_id, thread_id):
    to_get = [(Category, category_id), (Thread, thread_id)]
    return tuple([get_object_or_404(t, id=i) for (t, i) in to_get])


def get_forum_ctp(category_id, thread_id, post_id):
    to_get = [(Category, category_id), (Thread, thread_id), (Post, post_id)]
    return tuple([get_object_or_404(t, id=i) for (t, i) in to_get])


def get_msgs(request, forum=None):
    now = timezone.now()
    if forum is None:
        forum = request.contest.forum
    msgs = []
    if Ban.is_banned(forum, request.user):
        msgs.append(_("You are banned on this forum. You can't add, edit or "
                      "report posts. To appeal contact contest administrators.")
                    )
    if forum.is_locked(request.timestamp):
        msgs.append(_("This forum is locked, it is not possible to add "
                      "or edit posts right now"))
    if forum.lock_date and forum.lock_date > now and \
            not forum.is_locked(request.timestamp):
        localtime = timezone.localtime(forum.lock_date)
        msgs.append(_("Forum is going to be locked at %s") % \
                    localtime.strftime('%Y-%m-%d %H:%M:%S'))
    if forum.unlock_date and forum.unlock_date > now and \
            forum.is_locked(request.timestamp):
        localtime = timezone.localtime(forum.unlock_date)
        msgs.append(_("Forum is going to be unlocked at %s") % \
                    localtime.strftime('%Y-%m-%d %H:%M:%S'))
    return msgs
