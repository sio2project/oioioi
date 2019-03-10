from django.conf import settings
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError, ImproperlyConfigured
from django.db import models
from django.dispatch import Signal
from django.utils.translation import ugettext_lazy as _, \
    get_language_from_request, get_language
from mptt.models import MPTTModel, TreeForeignKey

from oioioi.base.utils.validators import (validate_db_string_id,
                                          validate_whitespaces)
from oioioi.portals.utils import join_paths

if 'oioioi.portals.processors.portal_processor' \
        not in settings.TEMPLATES[0]['OPTIONS']['context_processors']:
    raise ImproperlyConfigured("When using portals module "
                               "you have to add oioioi.portals.processors.portal_processor "
                               "to TEMPLATES[0]['OPTIONS']['context_processors'] in settings.py")


class Node(MPTTModel):
    short_name = models.CharField(max_length=32, verbose_name=_("short name"),
                                  help_text=_("Shown in the URL."),
                                  validators=[validate_db_string_id])
    parent = TreeForeignKey('self', null=True, blank=False,
                            related_name='children', verbose_name=_("parent"),
                            on_delete=models.CASCADE)

    problems_in_content = models.ManyToManyField('problems.problem',
                                                 blank=True)

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
        return self.get_lang_version().full_name

    # Tries to get a default language version for a current context (from
    # a given request, then a current thread and then from the settings). If
    # none matching version could be found, just return any.
    def get_lang_version(self, request=None):
        if request is not None:
            lang = get_language_from_request(request)
            try:
                return self.language_versions.get(language=lang)
            except NodeLanguageVersion.DoesNotExist:
                pass

        try:
            return self.language_versions.get(language=get_language())
        except NodeLanguageVersion.DoesNotExist:
            pass

        try:
            return self.language_versions.get(language=settings.LANGUAGE_CODE)
        except NodeLanguageVersion.DoesNotExist:
            pass

        return self.language_versions.first()

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


class NodeLanguageVersion(models.Model):
    node = models.ForeignKey(Node, related_name='language_versions',
                             on_delete=models.CASCADE)
    language = models.CharField(max_length=6, verbose_name=_("language code"))
    full_name = models.CharField(max_length=32, verbose_name=_("full name"),
                                 help_text=_("Shown in the navigation menu."),
                                 validators=[validate_whitespaces])
    panel_code = models.TextField(null=False, blank=True,
                                  verbose_name=_("panel code"))

    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None):
        try:
            existing_language_version = self.node.language_versions.get(
                language=self.language)
            if self.pk != existing_language_version.pk:
                raise ValueError('Creating NodeLanguageVersion for Node object'
                                 ' that already has a NodeLanguageVersion with'
                                 ' the given language.')
        except NodeLanguageVersion.DoesNotExist:
            pass

        return super(NodeLanguageVersion, self).save(
            force_insert=force_insert, force_update=force_update,
            using=using, update_fields=update_fields
        )


class Portal(models.Model):
    owner = models.OneToOneField(User, null=True, unique=True,
                                 on_delete=models.CASCADE)
    root = models.OneToOneField(Node, unique=True, on_delete=models.CASCADE)
    short_description = models.CharField(max_length=256, null=True,
                                         default=_("My portal."),
                                         verbose_name=_("short description"))
    is_public = models.BooleanField(default=False, verbose_name=_("is public"))
    link_name = models.CharField(max_length=40, null=True, unique=True,
                                 help_text=_("Shown in the URL."),
                                 validators=[validate_db_string_id])

    def clean(self):
        super(Portal, self).clean()
        if (self.owner is None) == (self.link_name is None):  # !xor
            raise ValidationError(_("Exactly one from following should be "
                                    "chosen: owner, link_name"))
