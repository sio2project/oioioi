from django.template.loader import render_to_string


def supervision_processor(request):
    is_under_supervision=request.is_under_supervision if hasattr(request, 'is_under_supervision') else False
    return {
        'is_under_supervision': is_under_supervision,
        'extra_navbar_right_supervision': render_to_string(
            'supervision/navbar-user-supervision.html',
            dict(is_under_supervision=is_under_supervision)),
    }
