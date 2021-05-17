import six
from django.conf import settings
from django.contrib.auth.models import User
from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.db import models
from django.dispatch import Signal

from django.utils.translation import get_language, get_language_from_request
from django.utils.translation import ugettext_lazy as _
from mptt.models import MPTTModel, TreeForeignKey

from oioioi.base.utils.validators import validate_db_string_id, validate_whitespaces

if (
    'oioioi.portals.processors.portal_processor'
    not in settings.TEMPLATES[0]['OPTIONS']['context_processors']
):
    raise ImproperlyConfigured(
        "When using portals module "
        "you have to add oioioi.portals.processors.portal_processor "
        "to TEMPLATES[0]['OPTIONS']['context_processors'] in settings.py"
    )



class Node(MPTTModel):
    short_name = models.CharField(
        max_length=32,
        verbose_name=_("short name"),
        help_text=_("Shown in the URL."),
        validators=[validate_db_string_id],
    )
    parent = TreeForeignKey(
        'self',
        null=True,
        blank=False,
        related_name='children',
        verbose_name=_("parent"),
        on_delete=models.CASCADE,
    )

    problems_in_content = models.ManyToManyField('problems.problem', blank=True)

    class Meta(object):
        unique_together = ('parent', 'short_name')

    def __str__(self):
        return six.text_type(self.get_lang_version().full_name)

    def get_lang_version(self, request=None):
        """Tries to get a default language version for a current context (from
        a given request, then a current thread and then from the settings). If
        none matching version could be found, just return any.
        """
        languages = [get_language_from_request(request)] if request is not None else []
        languages += [get_language(), settings.LANGUAGE_CODE]
        for lang in languages:
            try:
                return self.language_versions.get(language=lang)
            except NodeLanguageVersion.DoesNotExist:
                pass

        return self.language_versions.first()

    def get_siblings(self, include_self=False):
        """Wrapper around mptt get_siblings method.
        Does not consider two root nodes to be siblings.
        """
        if self.is_root_node():
            if include_self:
                return Node.objects.filter(pk=self.pk)
            else:
                return Node.objects.none()
        else:
            return super(Node, self).get_siblings(include_self)

    def get_path(self):
        return '/'.join(
            node.short_name for node in self.get_ancestors(include_self=True)
        ).lstrip('/')


class NodeLanguageVersion(models.Model):
    node = models.ForeignKey(
        Node, related_name='language_versions', on_delete=models.CASCADE
    )
    language = models.CharField(max_length=6, verbose_name=_("language code"))
    full_name = models.CharField(
        max_length=32,
        verbose_name=_("full name"),
        help_text=_("Shown in the navigation menu."),
        validators=[validate_whitespaces],
    )
    panel_code = models.TextField(null=False, blank=True, verbose_name=_("panel code"))

    class Meta(object):
        unique_together = ('node', 'language')


class Portal(models.Model):
    owner = models.OneToOneField(User, null=True, unique=True, on_delete=models.CASCADE)
    root = models.OneToOneField(Node, unique=True, on_delete=models.CASCADE)
    short_description = models.CharField(
        max_length=256,
        null=True,
        default=_("My portal."),
        verbose_name=_("short description"),
    )
    is_public = models.BooleanField(default=False, verbose_name=_("is public"))
    link_name = models.CharField(
        max_length=40,
        null=True,
        unique=True,
        help_text=_("Shown in the URL."),
        validators=[validate_db_string_id],
    )

    def clean(self):
        super(Portal, self).clean()
        if (self.owner is None) == (self.link_name is None):  # !xor
            raise ValidationError(
                _("Exactly one from the following should be chosen: owner, link_name")
            )
