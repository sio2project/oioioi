from django.template import Library
from oioioi.newsfeed.models import News

register = Library()


@register.inclusion_tag('newsfeed/newsfeed.html', takes_context=True)
def newsfeed(context):
    request = context['request']
    news_list = News.objects.order_by('-date').prefetch_related('versions')
    news_version_list = []

    for news in news_list:
        news_version_list.append(news.get_content(request))

    return {'news_version_list': news_version_list, 'request': request}
