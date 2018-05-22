from django.conf import settings
from django.shortcuts import get_object_or_404, redirect
from django.template.response import TemplateResponse
from django.utils.translation import get_language_from_request

from oioioi.base.permissions import enforce_condition, is_superuser
from oioioi.newsfeed.forms import NewsLanguageVersionFormset
from oioioi.newsfeed.models import News, NewsLanguageVersion


@enforce_condition(is_superuser)
def add_news_view(request):
    if request.method == 'POST':
        formset = NewsLanguageVersionFormset(request.POST)
        if formset.is_valid():
            instances = formset.save(commit=False)

            news = News()
            news.save()

            for news_language_version in instances:
                news_language_version.news = news
                news_language_version.save()

            for news_language_version in formset.deleted_objects:
                news_language_version.delete()

            return redirect('newsfeed')
    else:
        current_language = get_language_from_request(request)
        formset = NewsLanguageVersionFormset(
            initial=[
                {
                    'language': lang_short,
                    'DELETE': lang_short != current_language
                }
                for lang_short, lang_name in settings.LANGUAGES
            ],
            queryset=NewsLanguageVersion.objects.none(),
        )
    return TemplateResponse(request,
                            'newsfeed/news-add.html', {'formset': formset})


@enforce_condition(is_superuser)
def delete_news_view(request, news_id):
    news_item = get_object_or_404(News, id=news_id)
    news_item.delete()
    return redirect('newsfeed')


@enforce_condition(is_superuser)
def edit_news_view(request, news_id):
    news_item = get_object_or_404(News, id=news_id)
    if request.method == 'POST':
        formset = NewsLanguageVersionFormset(request.POST)
        if formset.is_valid():
            instances = formset.save(commit=False)

            for news_language_version in instances:
                news_language_version.news = news_item
                news_language_version.save()

            for news_language_version in formset.deleted_objects:
                news_language_version.delete()

            return redirect('newsfeed')
    else:
        current_language = get_language_from_request(request)
        languages = [
            lang_short for lang_short, lang_name in settings.LANGUAGES
        ]
        queryset = NewsLanguageVersion.objects.filter(news=news_item)

        for news_language_version in queryset:
            languages.remove(news_language_version.language)

        formset = NewsLanguageVersionFormset(
            initial=[
                {'language': lang, 'DELETE': lang != current_language}
                for lang in languages
            ],
            queryset=NewsLanguageVersion.objects.filter(news=news_item),
        )
    return TemplateResponse(request,
                            'newsfeed/news-edit.html', {'formset': formset})


def newsfeed_view(request):
    news_list = News.objects.order_by('-date').prefetch_related('versions')
    news_version_list = []

    for news in news_list:
        news_version_list.append(news.get_content(request))

    return TemplateResponse(request, 'newsfeed/newsfeed-view.html', {
        'news_version_list': news_version_list
    })
