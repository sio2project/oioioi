from oioioi.supervision.utils import is_user_under_supervision


def under_supervision(request):
    if hasattr(request, 'user'):
        return {
            'is_under_supervision': is_user_under_supervision(getattr(request, 'user'))
        }
    else:
        return {
            'is_under_supervision': False
        }
