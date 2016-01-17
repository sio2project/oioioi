import re

from django.template.loader import render_to_string

from oioioi.newsfeed.models import News


class NewsWidget(object):
    name = 'news'
    compiled_tag_regex = re.compile(
        r'\[\['                   # [[
        r'News\|([\s\S]+?)'       # News|News item id
        r'\]\](?!\])'             # ]]
    )

    def render(self, request, m):
        try:
            news_id = int(m.group(1).split('|')[-1].strip())
        except ValueError:
            news_id = None
        if news_id:
            news_item = News.objects.filter(id=news_id)
            if news_item:
                return render_to_string('newsfeed/widgets/news.html',
                                        {'news': news_item[0]})
        return m.group(0)


class NewsfeedWidget(object):
    name = 'newsfeed'
    compiled_tag_regex = re.compile(r'\[\[Newsfeed\]\]')

    def render(self, request, m):
        news_list = News.objects.order_by('-date')
        return render_to_string('newsfeed/widgets/newsfeed.html',
                                {'news_list': news_list,
                                 'request': request})
