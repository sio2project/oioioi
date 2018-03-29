from django.shortcuts import get_object_or_404, redirect
from django.template.response import TemplateResponse

from oioioi.base.permissions import enforce_condition, is_superuser
from oioioi.newsfeed.forms import NewsForm
from oioioi.newsfeed.models import News


@enforce_condition(is_superuser)
def add_news_view(request):
    if request.method == 'POST':
        form = NewsForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('newsfeed')
    else:
        form = NewsForm()
    return TemplateResponse(request,
                            'newsfeed/news-add.html', {'form': form})


@enforce_condition(is_superuser)
def delete_news_view(request, news_id):
    news_item = get_object_or_404(News, id=news_id)
    news_item.delete()
    return redirect('newsfeed')


@enforce_condition(is_superuser)
def edit_news_view(request, news_id):
    news_item = get_object_or_404(News, id=news_id)
    if request.method == 'POST':
        form = NewsForm(request.POST, instance=news_item)
        if form.is_valid():
            form.save()
            return redirect('newsfeed')
    else:
        form = NewsForm(instance=news_item)
    return TemplateResponse(request,
                            'newsfeed/news-edit.html', {'form': form})


def newsfeed_view(request):
    news_list = News.objects.order_by('-date')
    return TemplateResponse(request,
                            'newsfeed/newsfeed.html', {'news_list': news_list})
