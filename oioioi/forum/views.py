from django.conf import settings
from django.contrib import messages
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from django.http import HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_POST
from django.db.models import Count, Q

from oioioi.base.menu import menu_registry
from oioioi.base.permissions import enforce_condition, not_anonymous
from oioioi.base.utils.confirmation import confirmation_view
from oioioi.contests.menu import contest_admin_menu_registry
from oioioi.contests.utils import (
    can_admin_contest,
    can_enter_contest,
    contest_exists,
    is_contest_admin,
)
from oioioi.forum.forms import BanForm, NewThreadForm, PostForm, ReportForm
from oioioi.forum.models import Category, Post, PostReaction, post_reaction_types
from oioioi.forum.utils import (
    annotate_posts_with_current_user_reactions,
    can_interact_with_admins,
    can_interact_with_users,
    forum_exists,
    forum_exists_and_visible,
    get_forum_ct,
    get_forum_ctp,
    get_msgs,
    is_proper_forum,
    move_category,
)


# registering forum
@menu_registry.register_decorator(
    _("Forum"),
    lambda request: reverse('forum', kwargs={'contest_id': request.contest.id}),
    order=500,
)
@contest_admin_menu_registry.register_decorator(
    _("Forum"),
    lambda request: reverse(
        'oioioiadmin:forum_forum_change', args=(request.contest.forum.id,)
    ),
    is_contest_admin,
    order=50,
)
@enforce_condition(contest_exists & can_enter_contest)
@enforce_condition(forum_exists_and_visible & is_proper_forum)
def forum_view(request):
    category_set = request.contest.forum.category_set.annotate(
        thread_count=Count('thread', distinct=True),
        post_count=Count('thread__post', distinct=True),
        reported_count=Count(
            'thread__post',
            filter=Q(thread__post__reported=True),
            distinct=True
        )
    ).order_by('order').all()

    return TemplateResponse(
        request,
        'forum/forum.html',
        {
            'forum': request.contest.forum,
            'msgs': get_msgs(request),
            'can_interact_with_users': can_interact_with_users(request),
            'can_interact_with_admins': can_interact_with_admins(request),
            'is_locked': request.contest.forum.is_locked(),
            'category_set': category_set,
        },
    )


@enforce_condition(contest_exists & can_enter_contest)
@enforce_condition(forum_exists_and_visible & is_proper_forum)
def latest_posts_forum_view(request):
    posts = (
        Post.objects.filter(
            thread__category__forum=request.contest.forum.pk,
        )
        .select_related('thread')
        .order_by('-add_date')
    )
    posts = annotate_posts_with_current_user_reactions(request, posts)

    context = {
        'forum': request.contest.forum,
        'msgs': get_msgs(request),
        'post_set': posts,
        'posts_per_page': settings.FORUM_PAGE_SIZE,
        'can_interact_with_users': can_interact_with_users(request),
        'can_interact_with_admins': can_interact_with_admins(request),
    }

    return TemplateResponse(request, 'forum/latest_posts.html', context)


@enforce_condition(contest_exists & can_enter_contest)
@enforce_condition(forum_exists_and_visible & is_proper_forum)
def category_view(request, category_id):
    category = get_object_or_404(Category, id=category_id)
    threads = (
        category.thread_set.prefetch_related('post_set')
        .select_related('last_post', 'last_post__author')
        .all()
    )

    return TemplateResponse(
        request,
        'forum/category.html',
        {
            'forum': request.contest.forum,
            'category': category,
            'threads': threads,
            'msgs': get_msgs(request),
            'can_interact_with_users': can_interact_with_users(request),
            'can_interact_with_admins': can_interact_with_admins(request),
            'forum_threads_per_page': getattr(settings, 'FORUM_THREADS_PER_PAGE', 30),
        },
    )


@enforce_condition(contest_exists & can_enter_contest)
@enforce_condition(forum_exists_and_visible & is_proper_forum)
def thread_view(request, category_id, thread_id):
    category, thread = get_forum_ct(category_id, thread_id)
    forum = request.contest.forum

    posts = thread.post_set.select_related('author').order_by('add_date').all()
    posts = annotate_posts_with_current_user_reactions(request, posts)

    context = {
        'forum': forum,
        'category': category,
        'thread': thread,
        'msgs': get_msgs(request),
        'post_set': posts,
        'forum_posts_per_page': getattr(settings, 'FORUM_POSTS_PER_PAGE', 30),
        'can_interact_with_users': can_interact_with_users(request),
        'can_interact_with_admins': can_interact_with_admins(request),
    }

    if can_interact_with_users(request):
        if request.method == "POST":
            form = PostForm(request, request.POST)
            if form.is_valid():
                instance = form.save(commit=False)
                instance.author = request.user
                instance.thread = thread
                instance.add_date = request.timestamp
                instance.save()
                post_count = thread.post_set.count()
                page = (post_count - 1) // getattr(settings, 'FORUM_POSTS_PER_PAGE', 30) + 1
                forum_thread_redirect = redirect(
                    'forum_thread',
                    contest_id=request.contest.id,
                    category_id=category.id,
                    thread_id=thread.id,
                )
                forum_thread_redirect['Location'] += f'?page={page}'
                return forum_thread_redirect
        else:
            form = PostForm(request)
        context['form'] = form

    return TemplateResponse(request, 'forum/thread.html', context)


@enforce_condition(not_anonymous & contest_exists & can_enter_contest)
@enforce_condition(forum_exists_and_visible & is_proper_forum & can_interact_with_users)
def thread_add_view(request, category_id):
    category = get_object_or_404(Category, id=category_id)
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
                return redirect(
                    'forum_thread',
                    contest_id=request.contest.id,
                    category_id=category.id,
                    thread_id=instance.id,
                )
    else:
        form = NewThreadForm(request)

    return TemplateResponse(
        request,
        'forum/thread_add.html',
        {
            'forum': request.contest.forum,
            'category': category,
            'form': form,
            'msgs': get_msgs(request),
        },
    )


@enforce_condition(not_anonymous & contest_exists & can_enter_contest)
@enforce_condition(forum_exists_and_visible & is_proper_forum & can_interact_with_users)
def edit_post_view(request, category_id, thread_id, post_id):
    (category, thread, post) = get_forum_ctp(category_id, thread_id, post_id)
    is_admin = is_contest_admin(request)

    if not (post.author == request.user or is_admin):
        raise PermissionDenied

    if request.method == 'POST':
        form = PostForm(request, request.POST, instance=post)
        if form.is_valid():
            instance = form.save(commit=False)
            instance.approved = False
            instance.last_edit_date = request.timestamp
            instance.save()
            return redirect(
                'forum_thread',
                contest_id=request.contest.id,
                category_id=category.id,
                thread_id=thread.id,
            )
    else:
        form = PostForm(request, instance=post)

    return TemplateResponse(
        request,
        'forum/edit_post.html',
        {
            'forum': request.contest.forum,
            'category': category,
            'thread': thread,
            'form': form,
            'post': post,
            'msgs': get_msgs(request),
        },
    )


@enforce_condition(not_anonymous & contest_exists & can_enter_contest)
@enforce_condition(forum_exists_and_visible & is_proper_forum & can_interact_with_users)
def delete_post_view(request, category_id, thread_id, post_id):
    (category, thread, post) = get_forum_ctp(category_id, thread_id, post_id)
    is_admin = is_contest_admin(request)
    if not (  # we assert following:
        is_admin
        or (
            post.author == request.user
            # you can remove a post only if there is no post added after yours
            and not thread.post_set.filter(add_date__gt=post.add_date).exists()
            and post.can_be_removed()
        )
    ):
        raise PermissionDenied
    else:
        choice = confirmation_view(
            request, 'forum/confirm_delete_post.html', {'thread': thread, 'post': post}
        )
        if not isinstance(choice, bool):
            return choice
        if choice:
            post.delete()

            if not thread.post_set.exists():
                thread.delete()
                return redirect(
                    'forum_category',
                    contest_id=request.contest.id,
                    category_id=category.id,
                )

    return redirect(
        'forum_thread',
        contest_id=request.contest.id,
        category_id=category.id,
        thread_id=thread.id,
    )


@enforce_condition(not_anonymous & contest_exists & can_enter_contest)
@enforce_condition(
    forum_exists_and_visible & is_proper_forum & can_interact_with_admins
)
def report_post_view(request, category_id, thread_id, post_id):
    (category, thread, post) = get_forum_ctp(category_id, thread_id, post_id)

    context = {'category': category, 'thread': thread, 'post': post}

    if not post.reported and not post.approved:
        if request.method == "POST":
            form = ReportForm(request.POST, instance=post)
            if form.is_valid():
                instance = form.save(commit=False)
                instance.reported = True
                instance.reported_by = request.user
                instance.save()
                return redirect(
                    'forum_thread',
                    contest_id=request.contest.id,
                    category_id=category.id,
                    thread_id=thread.id,
                )
        else:
            form = ReportForm(instance=post)
        context['form'] = form

    return TemplateResponse(request, 'forum/confirm_report.html', context)


@enforce_condition(contest_exists & is_contest_admin)
@enforce_condition(forum_exists_and_visible & is_proper_forum)
@require_POST
def approve_post_view(request, category_id, thread_id, post_id):
    (category, thread, post) = get_forum_ctp(category_id, thread_id, post_id)
    post.approved = True
    post.save()
    return redirect(
        'forum_thread',
        contest_id=request.contest.id,
        category_id=category.id,
        thread_id=thread.id,
    )


@enforce_condition(contest_exists & is_contest_admin)
@enforce_condition(forum_exists_and_visible & is_proper_forum)
@require_POST
def revoke_approval_post_view(request, category_id, thread_id, post_id):
    (category, thread, post) = get_forum_ctp(category_id, thread_id, post_id)
    post.approved = False
    post.save()
    return redirect(
        'forum_thread',
        contest_id=request.contest.id,
        category_id=category.id,
        thread_id=thread.id,
    )


@enforce_condition(contest_exists & is_contest_admin)
@enforce_condition(forum_exists_and_visible & is_proper_forum)
@require_POST
def hide_post_view(request, category_id, thread_id, post_id):
    (category, thread, post) = get_forum_ctp(category_id, thread_id, post_id)
    post.hidden = True
    post.reported = False
    post.report_reason = ""
    post.save()
    return redirect(
        'forum_thread',
        contest_id=request.contest.id,
        category_id=category.id,
        thread_id=thread.id,
    )


@enforce_condition(contest_exists & is_contest_admin)
@enforce_condition(forum_exists_and_visible & is_proper_forum)
@require_POST
def show_post_view(request, category_id, thread_id, post_id):
    # Admin shows reported/hidden post again
    (category, thread, post) = get_forum_ctp(category_id, thread_id, post_id)
    post.hidden = False
    post.save()
    return redirect(
        'forum_thread',
        contest_id=request.contest.id,
        category_id=category.id,
        thread_id=thread.id,
    )


@enforce_condition(not_anonymous & contest_exists & can_enter_contest)
@enforce_condition(forum_exists_and_visible & is_proper_forum & can_interact_with_users)
@require_POST
def post_toggle_reaction(request, category_id, thread_id, post_id):
    (category, _, post) = get_forum_ctp(category_id, thread_id, post_id)
    redirect_url = post.get_in_thread_url()

    if not category.reactions_enabled:
        messages.error(request, _("Post reactions are not enabled."))
        return redirect(redirect_url)

    reaction_type = request.GET.get('reaction', '').upper()

    if not reaction_type or post_reaction_types.get(reaction_type, None) is None:
        messages.error(request, _("Invalid reaction type."))
        return redirect(redirect_url)

    reaction = post.reactions.filter(author=request.user.pk)
    if reaction.exists():
        reaction = reaction.first()
        if reaction.type_of_reaction == reaction_type:
            reaction.delete()
        else:
            reaction.type_of_reaction = reaction_type
            reaction.save(update_fields=['type_of_reaction'])
    else:
        PostReaction.objects.create(
            author=request.user, post_id=post.id, type_of_reaction=reaction_type
        )

    return redirect(redirect_url)


@enforce_condition(contest_exists & is_contest_admin)
@enforce_condition(forum_exists_and_visible & is_proper_forum)
@require_POST
def delete_thread_view(request, category_id, thread_id):
    category, thread = get_forum_ct(category_id, thread_id)
    choice = confirmation_view(request, 'forum/confirm_delete.html', {'elem': thread})
    if not isinstance(choice, bool):
        return choice
    if choice:
        thread.delete()
    return redirect(
        'forum_category', contest_id=request.contest.id, category_id=category.id
    )


@enforce_condition(contest_exists & is_contest_admin)
@enforce_condition(forum_exists_and_visible & is_proper_forum)
@require_POST
def delete_category_view(request, category_id):
    category = get_object_or_404(Category, id=category_id)
    choice = confirmation_view(request, 'forum/confirm_delete.html', {'elem': category})
    if not isinstance(choice, bool):
        return choice
    if choice:
        category.delete()
    return redirect('forum', contest_id=request.contest.id)


@enforce_condition(contest_exists & is_contest_admin)
@enforce_condition(forum_exists_and_visible & is_proper_forum)
@require_POST
def toggle_reactions_in_category(request, category_id):
    category = get_object_or_404(Category, id=category_id)
    category.reactions_enabled = not category.reactions_enabled
    category.save(update_fields=['reactions_enabled'])
    return redirect('forum', contest_id=request.contest.id)


@enforce_condition(contest_exists & is_contest_admin)
@enforce_condition(forum_exists_and_visible & is_proper_forum)
@require_POST
def move_up_category_view(request, category_id):
    if not move_category(category_id, "up"):
        return HttpResponseBadRequest("Category is already on the top")
    return redirect('forum', contest_id=request.contest.id)


@enforce_condition(contest_exists & is_contest_admin)
@enforce_condition(forum_exists_and_visible & is_proper_forum)
@require_POST
def move_down_category_view(request, category_id):
    if not move_category(category_id, "down"):
        return HttpResponseBadRequest("Category is already on the bottom")
    return redirect('forum', contest_id=request.contest.id)


@enforce_condition(contest_exists & is_contest_admin)
@enforce_condition(forum_exists_and_visible)
@require_POST
def lock_forum_view(request):
    forum = request.contest.forum
    forum.lock_date = request.timestamp
    if forum.unlock_date and forum.unlock_date <= forum.lock_date:
        forum.unlock_date = None
    forum.save()
    return redirect('forum', contest_id=request.contest.id)


@enforce_condition(contest_exists & is_contest_admin)
@enforce_condition(forum_exists_and_visible)
@require_POST
def unlock_forum_view(request):
    # Unlocking forum clears both lock & unlock dates, just like forum was
    # never meant to be locked. If admin changes his mind, he will
    # lock it again or set auto-locking in admin panel
    forum = request.contest.forum
    forum.unlock_date = None
    forum.lock_date = None
    forum.save()
    return redirect('forum', contest_id=request.contest.id)


@enforce_condition(contest_exists & is_contest_admin)
@enforce_condition(forum_exists)
def ban_user_view(request, user_id):
    # Banning user blocks any user interaction with forum, while still
    # allowing viewing forum contents.

    forum = request.contest.forum

    if 'next' in request.GET:
        redirect_url = request.GET['next']
    else:
        redirect_url = reverse('forum', kwargs={'contest_id': request.contest.id})

    user = get_object_or_404(User, id=user_id)
    if can_admin_contest(user, request.contest):
        messages.error(request, _("You can't ban an admin."))
        return redirect(redirect_url)

    if request.method == 'POST':
        form = BanForm(request.POST)
        if form.is_valid():
            instance = form.save(commit=False)
            instance.user = user
            instance.forum = request.contest.forum
            instance.admin = request.user
            instance.save()
            messages.success(request, _("Banned user: %s") % str(user))

            if form.cleaned_data['delete_reports']:
                removed_reports_count = Post.objects.filter(
                    reported=True, reported_by=user, thread__category__forum=forum
                ).update(reported=False, reported_by=None)
                messages.success(
                    request, _("Removed %d reports") % removed_reports_count
                )
            return redirect(redirect_url)
    else:
        form = BanForm()

    return TemplateResponse(
        request,
        'forum/ban_user.html',
        {
            'banned_user': user,
            'form': form,
            'next': redirect_url,
            'msgs': get_msgs(request),
        },
    )
