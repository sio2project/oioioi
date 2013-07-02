from django.template.response import TemplateResponse


def confirmation_view(request,
        template='simple-centered-confirmation.html', context=None):
    """Renders simple confirmation boxes.

       This function returns boolean if user has already confirmed/canceled
       action and :class:`~django.template.response.TemplateResponse`
       otherwise.
    """
    if context is None:
        context = {}

    if request.method == 'POST' and 'confirmation_sent' in request.POST:
        if 'confirmation' in request.POST:
            return True
        else:
            return False

    return TemplateResponse(request, template, context)
