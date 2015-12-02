import datetime
from django.db import models
from django.db.models.signals import post_save, post_delete
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.dispatch import receiver
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _

from oioioi.contests.models import Contest
from oioioi.contests.date_registration import date_registry


@date_registry.register('lock_date',
                        name_generator=(lambda obj: _("Lock the forum")))
@date_registry.register('unlock_date',
                        name_generator=(lambda obj: _("Unlock the forum")))
class Forum(models.Model):
    """Forum is connected with contest"""

    contest = models.OneToOneField(Contest)
    visible = models.BooleanField(default=True,
                                  verbose_name=
                                  _("forum is visible after lock"))
    lock_date = models.DateTimeField(blank=True, null=True,
                                     verbose_name=_("autolock date"))
    unlock_date = models.DateTimeField(blank=True, null=True,
                                       verbose_name=_("autounlock date"))

    class Meta(object):
        verbose_name = _("forum")
        verbose_name_plural = _("forums")

    def __unicode__(self):
        return '%(name)s' % dict(name=self.contest.name)

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

    forum = models.ForeignKey(Forum, verbose_name=_("forum"))
    name = models.CharField(max_length=255, verbose_name=_("category"))

    class Meta(object):
        verbose_name = _("category")
        verbose_name_plural = _("categories")

    def __unicode__(self):
        return '%(name)s' % dict(name=self.name)

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
        return reverse('oioioiadmin:forum_category_change', args=(self.id, ))


class Thread(models.Model):
    """Thread model - topic in a category"""

    category = models.ForeignKey(Category, verbose_name=_("category"))
    name = models.CharField(max_length=255, verbose_name=_("thread"))
    last_post = models.ForeignKey('Post', null=True, on_delete=models.SET_NULL,
            verbose_name=_("last post"), related_name='last_post_of')

    class Meta(object):
        ordering = ('-last_post__id',)
        verbose_name = _("thread")
        verbose_name_plural = _("threads")

    def __unicode__(self):
        return '%(name)s' % dict(name=self.name)

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
        return reverse('oioioiadmin:forum_thread_change', args=(self.id, ))


class Post(models.Model):
    """Post - the basic part of the forum """

    thread = models.ForeignKey(Thread, verbose_name=_("thread"))
    content = models.TextField(verbose_name=_("post"))
    add_date = models.DateTimeField(verbose_name=_("add date"),
                                    default=timezone.now, blank=True)
    last_edit_date = models.DateTimeField(verbose_name=_("last edit"),
                                          blank=True, null=True)
    author = models.ForeignKey(User, verbose_name=_("author"))
    reported = models.BooleanField(verbose_name=_("reported"), default=False)
    hidden = models.BooleanField(verbose_name=_("hidden"), default=False)
    reported_by = models.ForeignKey(User, null=True,
                                    related_name='%(class)s_user_reported')

    @property
    def edited(self):
        return bool(self.last_edit_date)

    class Meta(object):
        index_together = (('thread', 'add_date'),)
        ordering = ('add_date', )
        verbose_name = _("post")
        verbose_name_plural = _("posts")

    def __unicode__(self):
        return '%(content)s in %(thread)s' % dict(content=self.content,
                                                  thread=self.thread)

    def get_admin_url(self):
        return reverse('oioioiadmin:forum_post_change', args=(self.id, ))

    def get_in_thread_url(self):
        thread = self.thread
        thread_url = reverse('forum_thread',
                kwargs={'contest_id': thread.category.forum.contest_id,
                        'category_id': thread.category_id,
                        'thread_id': thread.id})
        post_url = '%s#forum-post-%d' % (thread_url, self.id)
        return post_url

    def can_be_removed(self):
        return bool((timezone.now() - self.add_date)
                    < datetime.timedelta(minutes=15))


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
