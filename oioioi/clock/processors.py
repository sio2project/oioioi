from django.template import Template, Context
from django.core.urlresolvers import reverse
from django.utils.translation import ungettext
from oioioi.messages.views import new_messages, visible_messages

TEMPLATE = '<li><a href="{{ link }}"><span class="label label-important">' \
    '{{ text }}</span></a></li>'

def navbar_clock_processor(request):
    timestamp = getattr(request, 'timestamp', None)
    if not timestamp:
        return {}
    html = '<li><a href="#" id="clock">%s</a></li>' % \
            (timestamp.strftime('%X'),)
    return {'extra_navbar_right_clock': html}
