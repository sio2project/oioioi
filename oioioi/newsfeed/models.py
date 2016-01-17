from django.db import models
from django.utils.translation import ugettext_lazy as _

from oioioi.base.utils.deps import check_django_app_dependencies


check_django_app_dependencies(__name__, ['oioioi.portals'])


class News(models.Model):
    date = models.DateTimeField(auto_now_add=True, verbose_name=_("date"))
    title = models.CharField(max_length=255, verbose_name=_("title"))
    content = models.TextField(verbose_name=_("content"))
