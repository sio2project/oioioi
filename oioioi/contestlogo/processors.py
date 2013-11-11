from django.template import Context, loader
from django.utils.functional import lazy
from django.core.urlresolvers import reverse
from oioioi.contestlogo.models import ContestLogo, ContestIcon
from oioioi.contests.utils import is_contest_admin


def logo_processor(request):
    if not getattr(request, 'contest', None):
        return {}

    if is_contest_admin(request):
        return {}

    def generator():
        try:
            instance = ContestLogo.objects.get(contest=request.contest)
            url = reverse('logo_image_view',
                    kwargs={'contest_id': request.contest.id})
        except ContestLogo.DoesNotExist:
            url = request.contest.controller.default_contestlogo_url()
        if not url:
            return ''
        context = Context({'url': url})
        template = loader.get_template('contestlogo/logo.html')
        return template.render(context)
    return {'extra_menu_top_contestlogo': lazy(generator, unicode)()}


def icon_processor(request):
    if not getattr(request, 'contest', None):
        return {}

    def generator():
        icon_list = ContestIcon.objects \
                .filter(contest=request.contest).order_by('pk')
        urls = [reverse('icon_image_view',
                kwargs={'icon_id': icon.pk, 'contest_id': request.contest.id})
                for icon in icon_list]
        if not urls:
            urls = request.contest.controller.default_contesticons_urls()
        template = loader.get_template('contestlogo/icon.html')
        htmls = [template.render(Context({'url': url})) for url in urls]
        return htmls
    return {'menu_icons': lazy(generator, list)()}
