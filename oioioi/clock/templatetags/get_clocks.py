from django import template
from django.utils import timezone
from django.utils.translation import ugettext as _
from oioioi.contests.models import Round
import time

register = template.Library()

@register.inclusion_tag('clock/navbar_clock.html', takes_context=True)
def navbar_clock(context):
    timestamp = getattr(context['request'], 'timestamp', None)
    if not timestamp:
        return {}
    if 'admin_time' in context['request'].session:
        return {'current_time': timezone.localtime(timestamp).strftime('%x %X'),
            'is_admin_time_set': True}
    return {'current_time': timezone.localtime(timestamp).strftime('%X'),
        'is_admin_time_set': False}

@register.inclusion_tag('clock/navbar_admin_clock.html', takes_context=True)
def navbar_admin_clock(context):
    result = navbar_clock(context)
    result['path'] = context['request'].path
    return result

@register.inclusion_tag('clock/navbar_countdown.html', takes_context=True)
def navbar_countdown(context):
    timestamp = getattr(context['request'], 'timestamp', None)
    contest = getattr(context['request'], 'contest', None)
    if not (timestamp and contest):
        return {}
    rounds_times = [contest.controller \
            .get_round_times(context['request'], round) \
            for round in Round.objects.filter(contest=contest)]
    next_rounds_times = filter(lambda rt: rt.is_future(timestamp),
            rounds_times)
    next_rounds_times.sort(key=lambda rt: rt.get_start())
    current_rounds_times = filter(lambda rt: rt.get_end(),
            filter(lambda rt: rt.is_active(timestamp), rounds_times))
    current_rounds_times.sort(key=lambda rt: rt.get_end())

    if current_rounds_times:
        countdown_text_description = _("%s left to the end of the round.")
        remaining_seconds = time.mktime((current_rounds_times[0].get_end())
                .timetuple()) - time.mktime(timestamp.timetuple())
        round_duration = time.mktime(current_rounds_times[0].get_end()
                .timetuple()) - time.mktime(current_rounds_times[0].get_start()
                    .timetuple())
        elapsed_part = 1 - 1. * remaining_seconds / round_duration
    elif next_rounds_times:
        countdown_text_description = _("%s left to the start of the round.")
        remaining_seconds = time.mktime((next_rounds_times[0].get_start()) \
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
        countdown_text_description = '%s'
        if round_duration:
            countdown_text = _("The round is over!")
        else:
            countdown_text = _("The round has started!")
    countdown_text = countdown_text_description % countdown_text

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
