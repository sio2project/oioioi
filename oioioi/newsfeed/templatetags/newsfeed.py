from django.template import Library
from oioioi.newsfeed.models import News

register = Library()


@register.inclusion_tag('newsfeed/newsfeed.html', takes_context=True)
def newsfeed(context):
    request = context['request']
    news_list = News.objects.order_by('-date')
    return {'news_list': news_list, 'request': request}
