from django.db import models
from django.utils.safestring import mark_safe
from django.utils.translation import get_language, get_language_from_request
from django.utils.translation import ugettext_lazy as _
from mistune import Markdown

from oioioi.base.utils.deps import check_django_app_dependencies

check_django_app_dependencies(__name__, ['oioioi.portals'])


class News(models.Model):
    date = models.DateTimeField(auto_now_add=True, verbose_name=_("date"))

    def get_content(self, request=None):
        if request is not None:
            lang = get_language_from_request(request)
            try:
                return self.versions.get(language=lang)
            except NewsLanguageVersion.DoesNotExist:
                pass

        try:
            return self.versions.get(language=get_language())
        except NewsLanguageVersion.DoesNotExist:
            return self.versions.first()


class NewsLanguageVersion(models.Model):
    """Represents a content of a news.
    News may have multiple versions - each in another language.
    """

    news = models.ForeignKey(News, related_name='versions', on_delete=models.CASCADE)
    language = models.CharField(max_length=6, verbose_name=_("language code"))
    title = models.CharField(max_length=255, verbose_name=_("title"))
    content = models.TextField(verbose_name=_("content"))

    def rendered_content(self):
        return mark_safe(Markdown(escape=True).render(self.content))

    def save(
        self, force_insert=False, force_update=False, using=None, update_fields=None
    ):
        try:
            existing_language_version = self.news.versions.get(language=self.language)
            if self is not existing_language_version:
                raise ValueError(
                    'Creating NewsLanguageVersion for News object'
                    ' that already has a NewsLanguageVersion with'
                    ' the given language.'
                )
        except NewsLanguageVersion.DoesNotExist:
            pass

        return super(NewsLanguageVersion, self).save(
            force_insert=force_insert,
            force_update=force_update,
            using=using,
            update_fields=update_fields,
        )
