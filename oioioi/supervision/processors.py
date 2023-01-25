from django.template.loader import render_to_string


def supervision_processor(request):
    return {
        'is_under_supervision': request.is_under_supervision,
        'extra_navbar_right_supervision': render_to_string(
            'supervision/navbar-user-supervision.html',
            dict(is_under_supervision=request.is_under_supervision)),
    }
