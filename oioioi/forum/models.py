import datetime
from django.db import models
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _

from oioioi.contests.models import Contest


class Forum(models.Model):
    """Forum is connected with contest"""

    contest = models.OneToOneField(Contest)
    visible = models.BooleanField(default=True,
                                  verbose_name=
                                  _("forum is visible after lock"))
    lock_date = models.DateTimeField(blank=True, null=True,
                                     verbose_name=_("set autolock date"))
    unlock_date = models.DateTimeField(blank=True, null=True,
                                       verbose_name=_("set autounlock date"))

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

    class Meta(object):
        ordering = ('-id',)
        verbose_name = _("thread")
        verbose_name_plural = _("threads")

    def __unicode__(self):
        return '%(name)s' % dict(name=self.name)

    def count_posts(self):
        return self.post_set.count()
    count_posts.short_description = _("Posts count")

    def count_reported(self):
        p = self.post_set.filter(reported=True)
        return p.count()
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

    def can_be_removed(self):
        return bool((timezone.now() - self.add_date)
                    < datetime.timedelta(minutes=15))
