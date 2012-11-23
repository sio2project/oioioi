from django import template
from django.utils import timezone
from django.utils.translation import ugettext as _
import time

register = template.Library()

@register.inclusion_tag('clock/navbar_clock.html', takes_context=True)
def navbar_clock(context):
    timestamp = getattr(context['request'], 'timestamp', None)
    if not timestamp:
        return {}
    return {'current_time': timezone.localtime(timestamp).strftime('%X')}

@register.inclusion_tag('clock/navbar_countdown.html', takes_context=True)
def navbar_countdown(context):
    timestamp = getattr(context['request'], 'timestamp', None)
    contest = getattr(context['request'], 'contest', None)
    if not (timestamp and contest):
        return {}
    next_rounds = contest.round_set.filter(end_date__gt=timestamp) \
        .order_by('start_date')
    current_rounds = next_rounds.filter(start_date__lt=timestamp) \
        .order_by('end_date')

    if current_rounds:
        countdown_text_sufix = _(" left to the end of the round.")
        remaining_seconds = time.mktime((current_rounds[0].end_date) \
            .timetuple()) - time.mktime(timestamp.timetuple())
        round_duration = time.mktime(current_rounds[0].end_date.timetuple()) - \
            time.mktime(current_rounds[0].start_date.timetuple())
        elapsed_part = 1 - 1. * remaining_seconds / round_duration
    elif next_rounds:
        countdown_text_sufix = _(" left to the start of the round.")
        remaining_seconds = time.mktime((next_rounds[0].start_date) \
            .timetuple()) - time.mktime(timestamp.timetuple())
        round_duration = 0
    else:
        return {}

    seconds = remaining_seconds % 60
    remaining_seconds /= 60
    minutes = int(remaining_seconds % 60)
    remaining_seconds /= 60
    hours = int(remaining_seconds % 24)
    remaining_seconds /= 24
    days = int(remaining_seconds)
    if days:
        countdown_text = '%dd %dh %dm %ds' % (days, hours, minutes, seconds)
    elif hours:
        countdown_text = '%dh %dm %ds' % (hours, minutes, seconds)
    elif minutes:
        countdown_text = '%dm %ds' % (minutes, seconds)
    elif seconds:
        countdown_text = '%ds' % seconds
    else:
        countdown_text_sufix = ''
        if round_duration:
            countdown_text = _("The round is over!")
        else:
            countdown_text = _("The round has started!")
    countdown_text += countdown_text_sufix

    if round_duration:
        if elapsed_part < 0.5:
            red = int(510 * elapsed_part)
            green = 255
        else:
            red = 255
            green = int(510 * (1 - elapsed_part))
        blue = 0
        bar_color = 'rgb(%d,%d,%d)' % (red, green, blue)
        elapsed_part = str(int(elapsed_part * 100)) + '%'
    else:
        bar_color = ''
        elapsed_part = ''

    return {'countdown_text': countdown_text, 'bar_color': bar_color,
        'elapsed_part': elapsed_part}
