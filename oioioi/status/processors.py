import json

from django.template.loader import render_to_string

from oioioi.base.utils import request_cached
from oioioi.status.utils import get_status


@request_cached
def status_processor(request):
    if not hasattr(request, 'contest') or not hasattr(request, 'session'):
        # Called by too early middleware
        return {}

    return {
        'extra_footer_outdated': render_to_string('status/outdated_modal.html'),
        'extra_head_status': render_to_string('status/initial_status.html',
            {'status': json.dumps(get_status(request))})
    }
