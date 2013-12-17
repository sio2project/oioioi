from django import template
from django.utils import timezone
from django.utils.translation import ungettext, ugettext as _
from oioioi.contests.utils import rounds_times
import time

register = template.Library()


@register.inclusion_tag('clock/navbar_clock.html', takes_context=True)
def navbar_clock(context):
    timestamp = getattr(context['request'], 'timestamp', None)
    if not timestamp:
        return {}
    if 'admin_time' in context['request'].session:
        return {'current_time': timezone.localtime(timestamp)
               .strftime('%x %X'), 'is_admin_time_set': True}
    return {'current_time': timezone.localtime(timestamp).strftime('%X'),
        'is_admin_time_set': False}


@register.inclusion_tag('clock/navbar_admin_clock.html', takes_context=True)
def navbar_admin_clock(context):
    result = navbar_clock(context)
    result['path'] = context['request'].get_full_path()
    return result


@register.inclusion_tag('clock/navbar_countdown.html', takes_context=True)
def navbar_countdown(context):
    timestamp = getattr(context['request'], 'timestamp', None)
    contest = getattr(context['request'], 'contest', None)
    if not (timestamp and contest):
        return {}
    rtimes = rounds_times(context['request']).values()
    next_rounds_times = [rt for rt in rtimes if rt.is_future(timestamp)]
    next_rounds_times.sort(key=lambda rt: rt.get_start())
    current_rounds_times = [rt for rt in rtimes
                            if rt.is_active(timestamp) and rt.get_end()]
    current_rounds_times.sort(key=lambda rt: rt.get_end())

    if current_rounds_times:
        countdown_destination = _("end of the round.")
        remaining_seconds = time.mktime((current_rounds_times[0].get_end())
                .timetuple()) - time.mktime(timestamp.timetuple())
        round_duration = time.mktime(current_rounds_times[0].get_end()
                .timetuple()) - time.mktime(current_rounds_times[0].get_start()
                    .timetuple())
        elapsed_part = 1 - 1. * remaining_seconds / round_duration
    elif next_rounds_times:
        countdown_destination = _("start of the round.")
        remaining_seconds = time.mktime((next_rounds_times[0].get_start())
            .timetuple()) - time.mktime(timestamp.timetuple())
        round_duration = 0
    else:
        return {}

    seconds = remaining_seconds % 60
    seconds_str = ungettext('%(seconds)d second ',
        '%(seconds)d seconds ', seconds) % {'seconds': seconds}
    remaining_seconds /= 60
    minutes = int(remaining_seconds % 60)
    minutes_str = ungettext('%(minutes)d minute ',
        '%(minutes)d minutes ', minutes) % {'minutes': minutes}
    remaining_seconds /= 60
    hours = int(remaining_seconds % 24)
    hours_str = ungettext('%(hours)d hour ',
        '%(hours)d hours ', hours) % {'hours': hours}
    remaining_seconds /= 24
    days = int(remaining_seconds)
    days_str = ungettext('%(days)d day ',
        '%(days)d days ', days) % {'days': days}
    if days:
        countdown_days = days_str + hours_str + minutes_str + seconds_str
        countdown_text = \
            ungettext('%(countdown_days)sleft to the %(countdown_dest)s',
                      '%(countdown_days)sleft to the %(countdown_dest)s',
                      days) % {'countdown_days': countdown_days,
                               'countdown_dest': countdown_destination}
    elif hours:
        countdown_hours = hours_str + minutes_str + seconds_str
        countdown_text = \
            ungettext('%(countdown_hours)sleft to the %(countdown_dest)s',
                      '%(countdown_hours)sleft to the %(countdown_dest)s',
                      hours) % {'countdown_hours': countdown_hours,
                                'countdown_dest': countdown_destination}
    elif minutes:
        countdown_minutes = minutes_str + seconds_str
        countdown_text = \
            ungettext('%(countdown_minutes)sleft to the %(countdown_dest)s',
                      '%(countdown_minutes)sleft to the %(countdown_dest)s',
                      minutes) % {'countdown_minutes': countdown_minutes,
                                  'countdown_dest': countdown_destination}
    elif seconds:
        countdown_seconds = seconds_str
        countdown_text = \
            ungettext('%(countdown_seconds)sleft to the %(countdown_dest)s',
                      '%(countdown_seconds)sleft to the %(countdown_dest)s',
                      seconds) % {'countdown_seconds': countdown_seconds,
                                  'countdown_dest': countdown_destination}
    else:
        if round_duration:
            countdown_text = _("The round is over!")
        else:
            countdown_text = _("The round has started!")

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
