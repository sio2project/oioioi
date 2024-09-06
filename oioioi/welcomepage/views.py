from django.conf import settings
from django.shortcuts import redirect
from django.template.response import TemplateResponse
from django.utils.translation import gettext_lazy as _
from django.utils.translation import get_language_from_request

from oioioi.base.main_page import register_main_page_view
from oioioi.base.permissions import enforce_condition, is_superuser
from oioioi.welcomepage.forms import WelcomePageMessageFormset
from oioioi.welcomepage.models import WelcomePageMessage


@register_main_page_view(order=100)
def welcome_page_view(request):
    current_language = get_language_from_request(request)
    try:
        welcome_page_msg = WelcomePageMessage.objects.get(language=current_language)
    except WelcomePageMessage.DoesNotExist:
        try:
            welcome_page_msg = WelcomePageMessage.objects.first()
        except WelcomePageMessage.DoesNotExist:
            welcome_page_msg = None
    return TemplateResponse(
        request,
        'welcomepage/welcome-page.html',
        {
            'title': _('Welcome to %(site_name)s') % {'site_name': settings.SITE_NAME},
            'welcome_page_msg': welcome_page_msg,
            'show_edit_button': is_superuser(request),
        },
    )


@enforce_condition(is_superuser)
def edit_welcome_page_view(request):
    if request.method == 'POST':
        formset = WelcomePageMessageFormset(request.POST)
        if formset.is_valid():
            instances = formset.save(commit=False)
            for instance in instances:
                instance.save()
            for instance in formset.deleted_objects:
                instance.delete()
            return redirect('welcome_page')
    else:
        current_language = get_language_from_request(request)
        instances = WelcomePageMessage.objects.all()
        languages = [lang_short for lang_short, _ in settings.LANGUAGES]
        for instance in instances:
            languages.remove(instance.language)
        formset = WelcomePageMessageFormset(
            initial=[
                {'language': lang, 'DELETE': lang != current_language}
                for lang in languages
            ],
            queryset=instances,
        )
    return TemplateResponse(
        request,
        'welcomepage/welcome-page-edit.html',
        {
            'formset': formset
        },
    )
