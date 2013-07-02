from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from oioioi.forum.models import Category, Post, Thread
from oioioi.base.utils import request_cached
from oioioi.base.permissions import make_condition, make_request_condition
from oioioi.contests.utils import is_contest_admin


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
def is_not_locked(request):
    # returns True if forum is not locked (or user is an admin)
    # it is used to strengthen 'forum_exists_and_viible'
    return (not request.contest.forum.is_locked(request.timestamp)) or \
            is_contest_admin(request)


def get_forum_objects(request, cat_id=None, thread_id=None, post_id=None,
                      lock_required=False):
    ret = []
    forum = request.contest.forum
    ret.append(forum)
    if cat_id:
        cat = get_object_or_404(Category, id=cat_id)
        ret.append(cat)
    if thread_id:
        thread = get_object_or_404(Thread, id=thread_id)
        ret.append(thread)
    if post_id:
        post = get_object_or_404(Post, id=post_id)
        ret.append(post)
    if lock_required:
        is_locked = request.contest.forum.is_locked(request.timestamp)
        ret.append(is_locked)
    return ret


def get_msgs(forum, request):
    now = timezone.now()
    if forum.is_locked(request.timestamp):
        return _("This forum is locked, it is not possible to add "
                 "or edit posts right now")
    if forum.lock_date and forum.lock_date > now and \
       not forum.is_locked(request.timestamp):
        localtime = timezone.localtime(forum.lock_date)
        return _("Forum is going to be locked at ") + \
                localtime.strftime('%Y-%m-%d %H:%M:%S')
    if forum.unlock_date and forum.unlock_date > now and \
       forum.is_locked(request.timestamp):
        localtime = timezone.localtime(forum.unlock_date)
        return _("Forum is going to be unlocked at ") + \
                localtime.strftime('%Y-%m-%d %H:%M:%S')
    return None
