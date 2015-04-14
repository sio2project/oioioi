from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import ugettext_lazy as _
from mptt.models import MPTTModel, TreeForeignKey
from oioioi.base.utils.validators import validate_db_string_id, \
        validate_whitespaces


class Node(MPTTModel):
    full_name = models.CharField(max_length=256, verbose_name=_("full name"),
                                 validators=[validate_whitespaces])
    short_name = models.CharField(max_length=32, verbose_name=_("short name"),
                                  validators=[validate_db_string_id])
    parent = TreeForeignKey('self', null=True, blank=False,
                            related_name='children', verbose_name=_("parent"))
    panel_code = models.TextField(null=False, blank=True,
                                  verbose_name=_("panel code"))

    class Meta(object):
        unique_together = (('parent', 'short_name'),)

    def __unicode__(self):
        return self.full_name


class Portal(models.Model):
    owner = models.OneToOneField(User, null=True, unique=True)
    root = models.OneToOneField(Node, unique=True)
