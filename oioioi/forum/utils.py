from django.db import models, transaction
from django.db.models import Max, Min
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from oioioi.base.permissions import make_condition, make_request_condition
from oioioi.base.utils import request_cached
from oioioi.base.utils.public_message import get_public_message
from oioioi.contests.utils import is_contest_admin
from oioioi.forum.models import (
    Ban,
    Category,
    Post,
    PostReaction,
    Thread,
    ForumMessage,
    NewPostMessage,
)
from oioioi.participants.utils import is_participant


@make_request_condition
def forum_exists(request):
    return (
        hasattr(request.contest, 'controller')
        and hasattr(request.contest.controller, 'create_forum')
        and request.contest.controller.create_forum
        and hasattr(request.contest, 'forum')
    )


@make_request_condition
@request_cached
def forum_exists_and_visible(request):
    # checks whether the forum exists and
    # - is locked & visible
    # - is not locked
    # - user is contest admin
    # TODO maybe logic error (exists and visible or admin),
    #  should be exists and (visible or admin)?
    return (
        forum_exists(request)
        and (
            not (
                request.contest.forum.is_locked(request.timestamp)
                and not request.contest.forum.visible
            )
        )
        or (is_contest_admin(request))
    )


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
    if is_contest_admin(request):
        return True
    if Ban.is_banned(request.contest.forum, request.user):
        return False
    if request.contest.forum.is_locked(request.timestamp):
        return False
    if request.contest.forum.only_for_registered and not is_participant(request):
        return False
    return True


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
    if request.user.is_authenticated and Ban.is_banned(forum, request.user):
        msgs.append(
            _(
                "You are banned on this forum. You can't add, edit or "
                "report posts. To appeal contact contest administrators."
            )
        )
    if forum.is_locked(request.timestamp):
        msgs.append(
            _(
                "This forum is locked, it is not possible to add "
                "or edit posts right now"
            )
        )
        if forum.unlock_date and forum.unlock_date > now:
            localtime = timezone.localtime(forum.unlock_date)
            msgs.append(
                _("Forum is going to be unlocked at %s")
                % localtime.strftime('%Y-%m-%d %H:%M:%S')
            )
    elif forum.lock_date and forum.lock_date > now:
        localtime = timezone.localtime(forum.lock_date)
        msgs.append(
            _("Forum is going to be locked at %s")
            % localtime.strftime('%Y-%m-%d %H:%M:%S')
        )

    return msgs


@transaction.atomic
def swap_categories_order(cat1, cat2, forum_categories):
    # this is needed because (forum, order) unique constraint would be violated
    # deferrable option for constraints will be added in django 3.1
    temp_order = forum_categories.aggregate(models.Max("order"))["order__max"] + 1
    old_cat1_order = cat1.order
    cat1.order = cat2.order
    cat2.order = temp_order
    cat2.save(update_fields=["order"])
    cat1.save(update_fields=["order"])
    cat2.order = old_cat1_order
    cat2.save(update_fields=["order"])


def move_category(category_id, direction):
    if direction not in ("up", "down"):
        raise ValueError("direction must be either up or down")

    category = get_object_or_404(Category, id=category_id)
    categories = category.forum.category_set

    agg_function, agg_name = {"up": (Min, "min"), "down": (Max, "max")}[direction]
    boundary_order = categories.aggregate(agg_function("order"))["order__" + agg_name]
    if category.order == boundary_order:
        return False

    if direction == "up":
        swap_with = categories.filter(order__lt=category.order).reverse()[0]
    else:
        swap_with = categories.filter(order__gt=category.order)[0]

    swap_categories_order(category, swap_with, categories)
    return True


def annotate_posts_with_current_user_reactions(request, qs):
    if request.user.is_anonymous:
        qs = qs.annotate(user_upvoted=models.Value(False, models.BooleanField()))
        qs = qs.annotate(user_downvoted=models.Value(False, models.BooleanField()))
    else:
        for f_name, rtype in [
            ('user_upvoted', 'UPVOTE'),
            ('user_downvoted', 'DOWNVOTE'),
        ]:
            qs = qs.annotate(
                **{
                    f_name: models.Exists(
                        PostReaction.objects.filter(
                            author=request.user,
                            type_of_reaction=rtype,
                            post=models.OuterRef('pk'),
                        )
                    )
                }
            )

    return qs


def get_forum_message(request):
    return get_public_message(
        request,
        ForumMessage,
        'forum_message',
    )


def get_new_post_message(request):
    return get_public_message(
        request,
        NewPostMessage,
        'forum_new_post_message',
    )
