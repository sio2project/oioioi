from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.utils import timezone
from django.utils.translation import string_concat
from django.utils.translation import ugettext_lazy as _
from django.utils.translation import ungettext_lazy

from oioioi.base import admin
from oioioi.base.utils import make_html_link
from oioioi.contests.admin import contest_site
from oioioi.contests.utils import is_contest_admin
from oioioi.forum.models import Category, Forum, Post, Thread


def make_list_elem(elem, text=None):
    if not text:
        text = elem.name
    return '<li>%s</li>' % make_html_link(elem.get_admin_url(), text)


def get_permission(self, request):
    try:
        _f = request.contest.forum
        return is_contest_admin(request)
    except Forum.DoesNotExist:
        return False


class ForumAdmin(admin.ModelAdmin):
    fields = ('visible', 'lock_date', 'unlock_date', 'categories',
              'add_category', 'posts_admin')
    readonly_fields = ('categories', 'add_category', 'posts_admin')

    def categories(self, obj):
        slist = [make_list_elem(c) for c in obj.category_set
                    .prefetch_related('thread_set', 'thread_set__post_set')
                    .all()]
        ret = "".join(slist)
        if not ret:
            ret = string_concat('<li>', _("Empty forum"), '</li>')
        return '<ul>%s</ul>' % ret
    categories.allow_tags = True
    categories.short_description = _("Categories")

    def add_category(self, obj):
        return make_html_link(reverse('oioioiadmin:forum_category_add',), '+')
    add_category.allow_tags = True
    add_category.short_description = _("Add category")

    def posts_admin(self, obj):
        return make_html_link(reverse('oioioiadmin:forum_post_changelist',),
                _("Posts admin view"))
    posts_admin.allow_tags = True
    posts_admin.short_description = _("Posts")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return get_permission(self, request)

    def has_delete_permission(self, request, obj=None):
        return False

    def response_change(self, request, obj):
        # Never redirect to the list of forums. Just re-display the edit
        # view.
        if '_popup' not in request.POST:
            return HttpResponseRedirect(request.get_full_path())
        return super(ForumAdmin, self).response_change(request, obj)

    def get_queryset(self, request):
        # each qs filters forum/categories/threads/posts connected with
        # this particular contest
        qs = super(ForumAdmin, self).get_queryset(request)
        qs = qs.filter(contest=request.contest)
        return qs


class CategoryAdmin(admin.ModelAdmin):
    fields = ('name', 'threads',)
    readonly_fields = ('threads',)

    def threads(self, obj):
        slist = [make_list_elem(t) for t in obj.thread_set
                    .prefetch_related('post_set').all()]
        ret = "".join(slist)
        if not ret:
            ret = string_concat('<li>', _("Empty category"), '</li>')
        return '<ul>%s</ul>' % ret
    threads.allow_tags = True
    threads.short_description = _("Threads")

    def save_model(self, request, obj, form, change):
        obj.forum = request.contest.forum
        obj.save()

    def has_add_permission(self, request):
        return get_permission(self, request)

    def has_change_permission(self, request, obj=None):
        return get_permission(self, request)

    def has_delete_permission(self, request, obj=None):
        return get_permission(self, request)

    def response_add(self, request, obj, post_url_continue=None):
        if '_popup' not in request.POST:
            return HttpResponseRedirect(
                reverse('oioioiadmin:forum_forum_change',
                args=(request.contest.forum.id,)))
        return super(CategoryAdmin, self).response_add(request, obj,
                                                       post_url_continue)

    def response_change(self, request, obj):
        if '_popup' not in request.POST:
            return HttpResponseRedirect(request.get_full_path())
        return super(CategoryAdmin, self).response_change(request, obj)

    def response_delete(self, request):
        if 'came_from' in request.GET or \
           not self.has_change_permission(request):
            return super(CategoryAdmin, self).response_delete(request)
        return HttpResponseRedirect(
            reverse('oioioiadmin:forum_forum_change',
            args=(request.contest.forum.id,)))

    def get_queryset(self, request):
        qs = super(CategoryAdmin, self).get_queryset(request)
        qs = qs.filter(forum=request.contest.forum)
        return qs


class ThreadAdmin(admin.ModelAdmin):
    fields = ['name', 'category', 'count_posts', 'count_reported', 'posts']
    readonly_fields = ('count_posts', 'count_reported', 'posts')

    def get_post_descr(self, post):
        localtime = timezone.localtime(post.add_date)
        return '#%(id)s. %(author)s: %(date)s' % {
            'id': post.id,
            'author': post.author,
            'date': localtime.strftime('%Y-%m-%d %H:%M:%S')
        }

    def posts(self, obj):
        slist = [make_list_elem(p, self.get_post_descr(p))
                 for p in obj.post_set.select_related('author').all()]
        ret = "".join(slist)
        if not ret:
            ret = string_concat('<li>', _("Empty thread"), '</li>')
        return '<ul>%s</ul>' % ret
    posts.allow_tags = True
    posts.short_description = _("Posts")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return get_permission(self, request)

    def has_delete_permission(self, request, obj=None):
        return get_permission(self, request)

    def response_add(self, request, obj, post_url_continue=None):
        if '_popup' not in request.POST:
            return HttpResponseRedirect(
                reverse('oioioiadmin:forum_forum_change',
                args=(request.contest.forum.id,)))
        return super(ThreadAdmin, self).response_add(request, obj,
                                                     post_url_continue)

    def response_change(self, request, obj):
        if '_popup' not in request.POST:
            return HttpResponseRedirect(request.get_full_path())
        return super(ThreadAdmin, self).response_change(request, obj)

    def response_delete(self, request):
        if 'came_from' in request.GET or \
           not self.has_change_permission(request):
            return super(ThreadAdmin, self).response_delete(request)
        return HttpResponseRedirect(
            reverse('oioioiadmin:forum_forum_change',
            args=(request.contest.forum.id,)))

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'category':
            kwargs['queryset'] = Category.objects.filter(
                forum=request.contest.forum)
        return super(ThreadAdmin, self) \
            .formfield_for_foreignkey(db_field, request, **kwargs)

    def get_queryset(self, request):
        qs = super(ThreadAdmin, self).get_queryset(request)
        qs = qs.filter(category__forum=request.contest.forum)
        return qs


class PostAdmin(admin.ModelAdmin):
    list_display = ['id', 'author', 'thread_link', 'content', 'reported',
            'hidden']
    list_display_links = ['id', 'reported', 'hidden']
    list_filter = ['reported', 'hidden', 'thread']
    actions = ['hide_action', 'unreport_action']
    fields = ['content', 'thread', 'author', 'reported', 'hidden']
    readonly_fields = ['author']

    def thread_link(self, obj):
        return make_html_link(obj.get_in_thread_url(), obj.thread.name)
    thread_link.allow_tags = True
    thread_link.short_description = _("Thread")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return get_permission(self, request)

    def has_delete_permission(self, request, obj=None):
        return get_permission(self, request)

    def response_change(self, request, obj):
        if '_popup' not in request.POST:
            return HttpResponseRedirect(request.get_full_path())
        return super(PostAdmin, self).response_change(request, obj)

    def response_delete(self, request):
        if 'came_from' in request.GET or \
           not self.has_change_permission(request):
            return super(PostAdmin, self).response_delete(request)
        return HttpResponseRedirect(
            reverse('oioioiadmin:forum_forum_change',
            args=(request.contest.forum.id,)))

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'thread':
            kwargs['queryset'] = Thread.objects.filter(
                category__forum=request.contest.forum)
        return super(PostAdmin, self) \
            .formfield_for_foreignkey(db_field, request, **kwargs)

    def hide_action(self, request, queryset):
        queryset.update(hidden=True)

        counter = queryset.count()
        self.message_user(
            request,
            ungettext_lazy("One post has been hidden.",
                           "%(counter)d posts have been hidden.",
                           counter)
                % {'counter': counter})
    hide_action.short_description = _("Hide selected posts")

    def unreport_action(self, request, queryset):
        queryset.update(reported=False)

        counter = queryset.count()
        self.message_user(
            request,
            ungettext_lazy("\"Reported\" status removed from one post.",
                           "\"Reported\" status removed from %(counter)d "
                           "posts.", counter)
                % {'counter': counter})
    unreport_action.short_description = _("Dismiss reports for selected posts")

    def get_queryset(self, request):
        qs = super(PostAdmin, self).get_queryset(request)
        qs = qs.filter(thread__category__forum=request.contest.forum)
        return qs

contest_site.contest_register(Forum, ForumAdmin)
contest_site.contest_register(Category, CategoryAdmin)
contest_site.contest_register(Thread, ThreadAdmin)
contest_site.contest_register(Post, PostAdmin)
