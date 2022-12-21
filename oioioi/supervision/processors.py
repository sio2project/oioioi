from django.template.loader import render_to_string
from oioioi.supervision.utils import is_user_under_supervision


def under_supervision(request):
    is_under_supervision = False
    if hasattr(request, 'user'):
        is_under_supervision=is_user_under_supervision(getattr(request, 'user'))
    return {
        'is_under_supervision': is_under_supervision,
        'extra_navbar_right_supervision': render_to_string('supervision/navbar-user-supervision.html',
                                                           dict(is_under_supervision=is_under_supervision)),
    }
