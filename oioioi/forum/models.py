import datetime

from django.contrib.auth.models import User
from django.db import models
from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver
from django.urls import reverse
from django.utils import timezone
from django.conf import settings

from django.utils.translation import gettext_lazy as _

from oioioi.base.fields import EnumField, EnumRegistry
from oioioi.base.models import PublicMessage
from oioioi.contests.date_registration import date_registry
from oioioi.contests.models import Contest


@date_registry.register('lock_date', name_generator=(lambda obj: _("Lock the forum")))
@date_registry.register(
    'unlock_date', name_generator=(lambda obj: _("Unlock the forum"))
)

class Forum(models.Model):
    """Forum is connected with contest"""

    contest = models.OneToOneField(Contest, on_delete=models.CASCADE)
    only_for_registered = models.BooleanField(
        default=True, verbose_name=_("allow only registered users to post on forum")
    )
    visible = models.BooleanField(
        default=True, verbose_name=_("forum is visible after lock")
    )
    lock_date = models.DateTimeField(
        blank=True, null=True, verbose_name=_("autolock date")
    )
    unlock_date = models.DateTimeField(
        blank=True, null=True, verbose_name=_("autounlock date")
    )

    class Meta(object):
        verbose_name = _("forum")
        verbose_name_plural = _("forums")

    def __str__(self):
        return u'%(name)s' % {u'name': self.contest.name}

    def is_autolocked(self, now=None):
        """Returns true if forum is locked"""
        if not now:
            now = timezone.now()
        return bool(self.lock_date and now >= self.lock_date)

    def is_autounlocked(self, now=None):
        """Returns true if forum was unlocked"""
        if not now:
            now = timezone.now()
        return bool(self.unlock_date and now >= self.unlock_date)

    def is_locked(self, now=None):
        """Returns true if forum is locked and not unlocked"""
        return bool(self.is_autolocked(now) and not self.is_autounlocked(now))



class Category(models.Model):
    """Category model """

    forum = models.ForeignKey(Forum, verbose_name=_("forum"), on_delete=models.CASCADE)
    name = models.CharField(max_length=255, verbose_name=_("category"))
    order = models.IntegerField(verbose_name=_("order"))
    reactions_enabled = models.BooleanField(
        default=False, verbose_name=_("reactions enabled")
    )

    class Meta(object):
        verbose_name = _("category")
        verbose_name_plural = _("categories")
        unique_together = ("forum", "order")
        ordering = ("order",)

    def __str__(self):
        return u"%s" % self.name

    def count_threads(self):
        return self.thread_set.count()

    count_threads.short_description = _("Threads count")

    def count_posts(self):
        ret = 0
        for t in self.thread_set.all():
            ret += t.count_posts()
        return ret

    count_posts.short_description = _("Posts count")

    def count_reported(self):
        ret = 0
        for t in self.thread_set.all():
            ret += t.count_reported()
        return ret

    count_reported.short_description = _("Reported posts count")

    def get_admin_url(self):
        return reverse('oioioiadmin:forum_category_change', args=(self.id,))

    def save(self, **kwargs):
        if self.pk is None:
            forum_categories = Category.objects.filter(forum__pk=self.forum_id)
            if forum_categories.exists():
                self.order = (
                    forum_categories.aggregate(models.Max("order"))["order__max"] + 1
                )
            else:
                self.order = 0

        super(Category, self).save(**kwargs)



class Thread(models.Model):
    """Thread model - topic in a category"""

    category = models.ForeignKey(
        Category, verbose_name=_("category"), on_delete=models.CASCADE
    )
    name = models.CharField(max_length=255, verbose_name=_("thread"))
    last_post = models.ForeignKey(
        'Post',
        null=True,
        on_delete=models.SET_NULL,
        verbose_name=_("last post"),
        related_name='last_post_of',
    )

    class Meta(object):
        ordering = ('-last_post__id',)
        verbose_name = _("thread")
        verbose_name_plural = _("threads")

    def __str__(self):
        return u'%(name)s' % {u'name': self.name}

    def count_posts(self):
        return self.post_set.count()

    count_posts.short_description = _("Posts count")

    def count_reported(self):
        # Although it may be done by:
        #   self.post_set.filter(reported=true).count()
        # such solution produces O(|threads|) queries on a forum/category view.
        # Moreover, it's not possible to prefetch them (like in count_posts):
        # http://stackoverflow.com/a/12974801/2874777
        return len([p for p in self.post_set.all() if p.reported])

    count_reported.short_description = _("Reported posts count")

    def get_admin_url(self):
        return reverse('oioioiadmin:forum_thread_change', args=(self.id,))



class Post(models.Model):
    """Post - the basic part of the forum """

    thread = models.ForeignKey(
        Thread, verbose_name=_("thread"), on_delete=models.CASCADE
    )
    content = models.TextField(verbose_name=_("post"))
    add_date = models.DateTimeField(
        verbose_name=_("add date"), default=timezone.now, blank=True
    )
    last_edit_date = models.DateTimeField(
        verbose_name=_("last edit"), blank=True, null=True
    )
    author = models.ForeignKey(User, verbose_name=_("author"), on_delete=models.CASCADE)
    reported = models.BooleanField(verbose_name=_("reported"), default=False)
    report_reason = models.TextField(
        verbose_name=_("report_reason"), default="", blank=True
    )
    approved = models.BooleanField(verbose_name=_("approved"), default=False)
    hidden = models.BooleanField(verbose_name=_("hidden"), default=False)
    reported_by = models.ForeignKey(
        User,
        null=True,
        related_name='%(class)s_user_reported',
        on_delete=models.SET_NULL,
    )

    class PostsWithReactionsSummaryManager(models.Manager):
        def get_queryset(self):
            qs = super(Post.PostsWithReactionsSummaryManager, self).get_queryset()

            for rtype, attr_name in POST_REACTION_TO_COUNT_ATTR.items():
                reaction_count_agg = {
                    attr_name: models.Count(
                        'reactions', 
                        filter=models.Q(reactions__type_of_reaction=rtype)
                    )
                }
                qs = qs.annotate(**reaction_count_agg)

            max_count = getattr(settings, 'FORUM_REACTIONS_TO_DISPLAY', 10)
            for rtype, attr_name in POST_REACTION_TO_PREFETCH_ATTR.items():
                qs = qs.prefetch_related(
                    models.Prefetch(
                        'reactions', 
                        to_attr=attr_name,
                        queryset=PostReaction.objects
                                .filter(type_of_reaction=rtype)
                                .order_by('-pk')
                                .select_related('author')[:max_count], 
                    )
                )

            return qs

    objects = PostsWithReactionsSummaryManager()

    @property
    def edited(self):
        return bool(self.last_edit_date)

    class Meta(object):
        indexes = [models.Index(fields=("thread", "add_date"))]
        ordering = ('add_date',)
        verbose_name = _("post")
        verbose_name_plural = _("posts")

    def __str__(self):
        return u'%(content)s in %(thread)s' % {
            u'content': self.content,
            u'thread': self.thread,
        }

    def get_admin_url(self):
        return reverse('oioioiadmin:forum_post_change', args=(self.id,))

    def get_in_thread_url(self):
        thread = self.thread
        thread_url = reverse(
            'forum_thread',
            kwargs={
                'contest_id': thread.category.forum.contest_id,
                'category_id': thread.category_id,
                'thread_id': thread.id,
            },
        )
        post_url = '%s#forum-post-%d' % (thread_url, self.id)
        return post_url

    def can_be_removed(self):
        return bool((timezone.now() - self.add_date) < datetime.timedelta(minutes=15))

    def is_author_banned(self):
        return Ban.is_banned(self.thread.category.forum, self.author)

    def is_reporter_banned(self):
        if not self.reported:
            return False

        return Ban.is_banned(self.thread.category.forum, self.reported_by)

POST_REACTION_TO_COUNT_ATTR = {
    "UPVOTE": "upvotes_count",
    "DOWNVOTE": "downvotes_count",
}

POST_REACTION_TO_PREFETCH_ATTR = {
    "UPVOTE": "upvoted_by",
    "DOWNVOTE": "downvoted_by",
}

post_reaction_types = EnumRegistry(
    entries=[
        ('UPVOTE', _("Upvote")),
        ('DOWNVOTE', _("Downvote")),
    ]
)


class PostReaction(models.Model):
    """PostReaction - represents a reaction to a post on the forum."""

    post = models.ForeignKey(
        Post,
        verbose_name=_("post"),
        related_name='reactions',
        on_delete=models.CASCADE,
    )
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    type_of_reaction = EnumField(post_reaction_types)



class Ban(models.Model):
    """Ban model - represents a ban on a forum. Banned person should not be
    allowed any 'write' interaction with forum. This includes reporting
    posts."""

    user = models.ForeignKey(User, verbose_name=_("user"), on_delete=models.CASCADE)
    forum = models.ForeignKey(Forum, verbose_name=_("forum"), on_delete=models.CASCADE)
    admin = models.ForeignKey(
        User,
        verbose_name=_("admin who banned"),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_forum_ban_set',
    )
    created_at = models.DateTimeField(
        auto_now_add=True, editable=False, verbose_name=_("banned at")
    )
    reason = models.TextField(verbose_name=_("reason"))

    @staticmethod
    def is_banned(forum, user):
        if user.is_anonymous:
            return False
        return Ban.objects.filter(forum=forum, user=user).exists()

    def __str__(self):
        return str(self.user)


@receiver(post_save, sender=Post)
def _set_as_new_last_post(sender, instance, created, **kwargs):
    if created:
        thread = instance.thread
        thread.last_post = instance
        thread.save()


@receiver(post_delete, sender=Post)
def _update_last_post(sender, instance, **kwargs):
    try:
        thread = instance.thread
    except Thread.DoesNotExist:
        # This may happen during cascade model deleting
        return
    try:
        thread.last_post = thread.post_set.latest('id')
    except Post.DoesNotExist:
        thread.last_post = None
    thread.save()


@receiver(pre_save, sender=Post)
def _remove_reports_if_approved(sender, instance, **kwargs):
    if instance.approved:
        instance.reported = False
        instance.reported_by = None


class ForumMessage(PublicMessage):
    class Meta(object):
        verbose_name = _("forum message")
        verbose_name_plural = _("forum messages")


class NewPostMessage(PublicMessage):
    class Meta(object):
        verbose_name = _("new post message")
        verbose_name_plural = _("new post messages")
