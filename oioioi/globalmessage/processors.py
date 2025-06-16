from django.template.loader import render_to_string
from django.utils import timezone

from oioioi.base.utils import request_cached
from oioioi.globalmessage.models import GlobalMessage


@request_cached
def global_message_processor(request):
    message = GlobalMessage.get_singleton()

    # Sometimes timestamp is not present in request (e.g. some cases of
    # 500 errors). If that's the case, fallback to current server time.
    time = getattr(request, 'timestamp', timezone.now())

    if message.visible(time):
        return {
            'extra_body_global_message': render_to_string(
                'global-message-user.html', {'global_message': message, 'start': message.start.strftime('%s') if message.start else ''}
            ),
            'extra_admin_global_message': render_to_string(
                'global-message-admin.html', {'global_message': message, 'start': message.start.strftime('%s') if message.start else ''}
            ),
        }

    return {}
