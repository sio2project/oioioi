import json

from django.template.loader import render_to_string
from django.utils.functional import lazy

from oioioi.base.utils import request_cached
from oioioi.status.utils import get_status


@request_cached
def status_processor(request):
    if not hasattr(request, 'contest') or not hasattr(request, 'session'):
        # Called by too early middleware
        return {}

    def outdated_generator():
        return render_to_string('status/outdated_modal.html')

    def status_generator():
        return render_to_string('status/initial_status.html',
            {'status': get_status(request)})

    # Well, we want to generate the status JSON as late as possible, for the
    # following simple/stupid reason: we want the current time in the response
    # to be generated as close to receiving it by the user as possible.
    # We don't want the clock to be off by the time of all our nasty,
    # unoptimized, grey database queries!

    return {'extra_footer_outdated': lazy(outdated_generator, unicode)(),
            'extra_footer_status': lazy(status_generator, unicode)()}
