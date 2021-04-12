import six
from django.urls import reverse
from django.template import loader
from django.utils.functional import lazy

from oioioi.base.utils import memoized
from oioioi.contestlogo.models import ContestIcon, ContestLogo
from oioioi.contests.utils import is_contest_admin


def logo_processor(request):
    if not getattr(request, 'contest', None):
        return {}

    if is_contest_admin(request):
        return {}

    @memoized
    def generator():
        try:
            instance = ContestLogo.objects.get(contest=request.contest)
            url = reverse('logo_image_view', kwargs={'contest_id': request.contest.id})
            link = instance.link
        except ContestLogo.DoesNotExist:
            url = request.contest.controller.default_contestlogo_url()
            link = request.contest.controller.default_contestlogo_link()

        if not url:
            return ''

        if not link:
            link = reverse(
                'default_contest_view', kwargs={'contest_id': request.contest.id}
            )
        context = {'url': url, 'link': link}
        template = loader.get_template('contestlogo/logo.html')
        return template.render(context)

    return {'extra_menu_top_contestlogo': lazy(generator, six.text_type)()}


def icon_processor(request):
    if not getattr(request, 'contest', None):
        return {}

    @memoized
    def generator():
        icon_list = ContestIcon.objects.filter(contest=request.contest).order_by('pk')
        urls = [
            reverse(
                'icon_image_view',
                kwargs={'icon_id': icon.pk, 'contest_id': request.contest.id},
            )
            for icon in icon_list
        ]
        if not urls:
            urls = request.contest.controller.default_contesticons_urls()
        template = loader.get_template('contestlogo/icon.html')
        htmls = [template.render({'url': url}) for url in urls]
        return htmls

    return {'menu_icons': lazy(generator, list)()}
