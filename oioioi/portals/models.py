from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import ugettext_lazy as _
from django.dispatch import Signal
from mptt.models import MPTTModel, TreeForeignKey
from oioioi.base.utils.validators import validate_db_string_id, \
        validate_whitespaces
from oioioi.portals.utils import join_paths


class Node(MPTTModel):
    full_name = models.CharField(max_length=32, verbose_name=_("full name"),
                                 help_text=_("Shown in the navigation menu."),
                                 validators=[validate_whitespaces])
    short_name = models.CharField(max_length=32, verbose_name=_("short name"),
                                  help_text=_("Shown in the URL."),
                                  validators=[validate_db_string_id])
    parent = TreeForeignKey('self', null=True, blank=False,
                            related_name='children', verbose_name=_("parent"))
    panel_code = models.TextField(null=False, blank=True,
                                  verbose_name=_("panel code"))

    class Meta(object):
        unique_together = (('parent', 'short_name'),)

    def __init__(self, *args, **kwargs):
        super(Node, self).__init__(*args, **kwargs)

        self._path = None
        self._connected_parent = None
        self._path_changed = Signal(providing_args=['path'])

    def save(self, *args, **kwargs):
        super(Node, self).save(*args, **kwargs)

        if self._path is not None:
            old_path = self._path
            self._path = None
            new_path = self.get_path()

            if old_path != new_path:
                self._path_changed.send(self, path=new_path)

    def __unicode__(self):
        return self.full_name

    def get_siblings(self, include_self=False):
        if self.is_root_node():
            if include_self:
                return Node.objects.filter(pk=self.pk)
            else:
                return Node.objects.none()
        else:
            return super(Node, self).get_siblings(include_self)

    def get_ancestors_including_self(self):
        return self.get_ancestors(include_self=True)

    def get_siblings_including_self(self):
        return self.get_siblings(include_self=True)

    def get_path(self):
        if self._path is None:
            if self.is_root_node():
                self._path = self.short_name
            else:
                self._path = join_paths(self.parent.get_path(),
                                        self.short_name)

                if self._connected_parent != self.parent:
                    if self._connected_parent is not None:
                        self._connected_parent._path_changed.disconnect(
                                self._parent_path_changed_callback)
                    if self.parent is not None:
                        self.parent._path_changed.connect(
                                self._parent_path_changed_callback)
                    self._connected_parent = self.parent

        return self._path

    def _parent_path_changed_callback(self, sender, path, **kwargs):
        self._path = join_paths(path, self.short_name)
        self._path_changed.send(self, path=self._path)


class Portal(models.Model):
    owner = models.OneToOneField(User, null=True, unique=True)
    root = models.OneToOneField(Node, unique=True)
