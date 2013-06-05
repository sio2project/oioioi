from django.core.exceptions import PermissionDenied
from django.core.urlresolvers import reverse
from django.shortcuts import redirect
from django.template.response import TemplateResponse
from django.utils.translation import ugettext_lazy as _
from django.views.decorators.http import require_POST
from oioioi.base.menu import menu_registry
from oioioi.base.permissions import enforce_condition, not_anonymous
from oioioi.base.utils.confirmation import confirmation_view
from oioioi.contests.utils import contest_exists, can_enter_contest, \
        is_contest_admin
from oioioi.contests.menu import contest_admin_menu_registry
from oioioi.forum.forms import PostForm, NewThreadForm
from oioioi.forum.utils import forum_exists_and_visible, is_proper_forum, \
        is_not_locked, get_forum_objects, get_msgs


# registering forum
@menu_registry.register_decorator(_("Forum"), lambda request:
        reverse('forum', kwargs={'contest_id': request.contest.id}),
    order=500)
@contest_admin_menu_registry.register_decorator(_("Forum"), lambda request:
        reverse('oioioiadmin:forum_forum_change',
                args=(request.contest.forum.id,)),
    order=50)
@enforce_condition(contest_exists & can_enter_contest)
@enforce_condition(forum_exists_and_visible & is_proper_forum)
def forum_view(request, contest_id):
    (forum, lock) = get_forum_objects(request, lock_required=True)
    msgs = get_msgs(forum, request)
    return TemplateResponse(request, 'forum/forum.html', {'forum': forum,
                                                          'msgs': msgs,
                                                          'is_locked': lock})


@enforce_condition(contest_exists & can_enter_contest)
@enforce_condition(forum_exists_and_visible & is_proper_forum)
def category_view(request, contest_id, category_id):
    (forum, category, lock) = get_forum_objects(request, category_id,
                                           lock_required=True)
    msgs = get_msgs(forum, request)
    return TemplateResponse(request, 'forum/category.html',
        {'forum': forum, 'category': category, 'msgs': msgs,
         'is_locked': lock})


@enforce_condition(contest_exists & can_enter_contest)
@enforce_condition(forum_exists_and_visible & is_proper_forum)
def thread_view(request, contest_id, category_id, thread_id):
    (forum, category, thread, lock) = get_forum_objects(request,
                                                  category_id, thread_id,
                                                  lock_required=True)
    msgs = get_msgs(forum, request)
    if (request.user.is_authenticated() and
       not request.contest.forum.is_locked(request.timestamp)) or \
       is_contest_admin(request):
        if request.method == "POST":
            form = PostForm(request, request.POST)
            if form.is_valid():
                instance = form.save(commit=False)
                instance.author = request.user
                instance.thread = thread
                instance.add_date = request.timestamp
                instance.save()
                return redirect('forum_thread', contest_id=contest_id,
                                category_id=category.id,
                                thread_id=thread.id)
        else:
            form = PostForm(request)

        return TemplateResponse(request, 'forum/thread.html',
            {'forum': forum, 'category': category, 'thread': thread,
             'form': form, 'msgs': msgs, 'is_locked': lock})
    else:
        return TemplateResponse(request, 'forum/thread.html',
            {'forum': forum, 'category': category, 'thread': thread,
             'msgs': msgs, 'is_locked': lock})


@enforce_condition(not_anonymous & contest_exists & can_enter_contest)
@enforce_condition(forum_exists_and_visible & is_proper_forum & is_not_locked)
def thread_add_view(request, contest_id, category_id):
    (forum, category,) = get_forum_objects(request, category_id)
    msgs = get_msgs(forum, request)
    if request.method == 'POST':
        form = NewThreadForm(request, request.POST)
        if form.is_valid():  # adding the new thread
            instance = form.save(commit=False)
            instance.category = category
            instance.save()
            post = PostForm(request, request.POST)
            if post.is_valid():  # adding the new post
                inst_post = post.save(commit=False)
                inst_post.author = request.user
                inst_post.thread = instance
                inst_post.add_date = request.timestamp
                inst_post.save()
                return redirect('forum_thread', contest_id=contest_id,
                                category_id=category.id,
                                thread_id=instance.id)
    else:
        form = NewThreadForm(request)

    return TemplateResponse(request, 'forum/thread_add.html',
        {'forum': forum, 'category': category, 'form': form, 'msgs': msgs})


@enforce_condition(not_anonymous & contest_exists & can_enter_contest)
@enforce_condition(forum_exists_and_visible & is_proper_forum & is_not_locked)
def edit_post_view(request, contest_id, category_id, thread_id, post_id):
    (forum, cat, thread, post) = get_forum_objects(request,
                                                   category_id, thread_id,
                                                   post_id)
    msgs = get_msgs(forum, request)
    is_admin = is_contest_admin(request)
    if post.author != request.user and not is_admin:
        raise PermissionDenied
    if request.method == 'POST':
        form = PostForm(request, request.POST, instance=post)
        if form.is_valid():
            instance = form.save(commit=False)
            instance.last_edit_date = request.timestamp
            instance.save()
            return redirect('forum_thread', contest_id=contest_id,
                            category_id=cat.id,
                            thread_id=thread.id)
    else:
        form = PostForm(request, instance=post)

    return TemplateResponse(request, 'forum/edit_post.html',
        {'forum': forum, 'category': cat, 'thread': thread, 'form': form,
         'post': post, 'msgs': msgs})


@enforce_condition(not_anonymous & contest_exists & can_enter_contest)
@enforce_condition(forum_exists_and_visible & is_proper_forum & is_not_locked)
def delete_post_view(request, contest_id, category_id, thread_id, post_id):
    (forum, cat, thread, post) = get_forum_objects(request,
                                                   category_id, thread_id,
                                                   post_id)
    is_admin = is_contest_admin(request)
    if not is_admin and \
       (post.author != request.user or
       (post.author == request.user and
       (thread.post_set.filter(add_date__gt=post.add_date).exists() or
        not post.can_be_removed()))):
        # author: if there are other posts added later or timedelta is gt 15min
        # if user is not the author of the post or forum admin
        raise PermissionDenied
    else:
        choice = confirmation_view(request, 'forum/confirm_delete.html',
                {'elem': post})
        if not isinstance(choice, bool):
            return choice
        if choice:
            post.delete()
            if not thread.post_set.exists():
                thread.delete()
                return redirect('forum_category', contest_id=contest_id,
                                category_id=cat.id)
    return redirect('forum_thread', contest_id=contest_id,
                    category_id=cat.id, thread_id=thread.id)


@enforce_condition(not_anonymous & contest_exists & can_enter_contest)
@enforce_condition(forum_exists_and_visible & is_proper_forum)
@require_POST
def report_post_view(request, contest_id, category_id, thread_id, post_id):
    (forum, category, thread, post) = get_forum_objects(request,
                                                        category_id, thread_id,
                                                        post_id)
    post.reported = True
    post.save()
    return redirect('forum_thread', contest_id=contest_id,
                    category_id=category.id, thread_id=thread.id)


@enforce_condition(contest_exists & is_contest_admin)
@enforce_condition(forum_exists_and_visible & is_proper_forum)
@require_POST
def hide_post_view(request, contest_id, category_id, thread_id, post_id):
    (forum, category, thread, post) = get_forum_objects(request,
                                                        category_id, thread_id,
                                                        post_id)
    post.hidden = True
    post.reported = False
    post.save()
    return redirect('forum_thread', contest_id=contest_id,
                    category_id=category.id, thread_id=thread.id)


@enforce_condition(contest_exists & is_contest_admin)
@enforce_condition(forum_exists_and_visible & is_proper_forum)
@require_POST
def show_post_view(request, contest_id, category_id, thread_id, post_id):
    # Admin shows reported/hidden post again
    (forum, category, thread, post) = get_forum_objects(request,
                                                        category_id, thread_id,
                                                        post_id)
    post.hidden = False
    post.save()
    return redirect('forum_thread', contest_id=contest_id,
                    category_id=category.id, thread_id=thread.id)


@enforce_condition(contest_exists & is_contest_admin)
@enforce_condition(forum_exists_and_visible & is_proper_forum & is_not_locked)
@require_POST
def delete_thread_view(request, contest_id, category_id, thread_id):
    (forum, category, thread) = get_forum_objects(request,
                                                  category_id, thread_id)
    choice = confirmation_view(request, 'forum/confirm_delete.html',
                               {'elem': thread})
    if not isinstance(choice, bool):
        return choice
    if choice:
        thread.delete()
    return redirect('forum_category', contest_id=contest_id,
                    category_id=category.id)


@enforce_condition(contest_exists & is_contest_admin)
@enforce_condition(forum_exists_and_visible & is_proper_forum & is_not_locked)
@require_POST
def delete_category_view(request, contest_id, category_id):
    (forum, category,) = get_forum_objects(request, category_id)
    choice = confirmation_view(request, 'forum/confirm_delete.html',
                               {'elem': category})
    if not isinstance(choice, bool):
        return choice
    if choice:
        category.delete()
    return redirect('forum', contest_id=contest_id)


@enforce_condition(contest_exists & is_contest_admin)
@enforce_condition(forum_exists_and_visible & is_not_locked)
@require_POST
def lock_forum_view(request, contest_id):
    forum = request.contest.forum
    forum.lock_date = request.timestamp
    if forum.unlock_date and forum.unlock_date <= forum.lock_date:
        forum.unlock_date = None
    forum.save()
    return redirect('forum', contest_id=contest_id)


@enforce_condition(contest_exists & is_contest_admin)
@enforce_condition(forum_exists_and_visible)
@require_POST
def unlock_forum_view(request, contest_id):
    # Unlocking forum clears both lock & unlock dates, just like forum was
    # never meant to be locked. If admin changes his mind, he will
    # lock it again or set auto-locking in admin panel
    forum = request.contest.forum
    forum.unlock_date = None
    forum.lock_date = None
    forum.save()
    return redirect('forum', contest_id=contest_id)
