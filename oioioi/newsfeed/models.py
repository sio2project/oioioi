import mistune
from django.db import models
from django.utils.safestring import mark_safe
from django.utils.translation import get_language, get_language_from_request
from django.utils.translation import gettext_lazy as _
from mistune.util import safe_entity

from oioioi.base.utils.deps import check_django_app_dependencies

check_django_app_dependencies(__name__, ["oioioi.portals"])


class NewsRenderer(mistune.HTMLRenderer):
    def text(self, text):
        # Keep HTML entities written by authors (e.g. &nbsp;) working, as in mistune 0.8.
        return safe_entity(text)


_markdown = mistune.create_markdown(renderer=NewsRenderer(escape=True), plugins=["strikethrough", "footnotes", "table", "url"])


class News(models.Model):
    date = models.DateTimeField(auto_now_add=True, verbose_name=_("date"))

    def get_content(self, request=None):
        # This makes .prefetch_related('versions') work. Inspired by Problem.name.
        versions_list = [version for version in self.versions.all()]
        versions = {version.language: version for version in versions_list}
        if request is not None:
            lang = get_language_from_request(request)
            if lang in versions:
                return versions[lang]

        return versions.get(get_language(), versions_list[0])


class NewsLanguageVersion(models.Model):
    """Represents a content of a news.
    News may have multiple versions - each in another language.
    """

    news = models.ForeignKey(News, related_name="versions", on_delete=models.CASCADE)
    language = models.CharField(max_length=6, verbose_name=_("language code"))
    title = models.CharField(max_length=255, verbose_name=_("title"))
    content = models.TextField(verbose_name=_("content"))

    def rendered_content(self):
        return mark_safe(_markdown(self.content))

    def save(self, *args, **kwargs):
        try:
            existing_language_version = self.news.versions.get(language=self.language)
            if self != existing_language_version:
                raise ValueError("Creating NewsLanguageVersion for News object that already has a NewsLanguageVersion with the given language.")
        except NewsLanguageVersion.DoesNotExist:
            pass

        return super().save(*args, **kwargs)
