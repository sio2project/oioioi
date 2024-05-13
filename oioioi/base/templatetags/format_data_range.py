from django import template
from django.utils import formats

register = template.Library()

@register.simple_tag
def format_data_range(start, end):
    if start is not None and end is not None:
        if start.year == end.year and start.month == end.month and start.day == end.day:
            day = formats.date_format(start, "j E Y")
            start_str = formats.date_format(start, "H:i")
            end_str = formats.date_format(end, "H:i")
            return '(' + day + ', ' + start_str + ' - ' + end_str + ')'

    start_str = ''
    if start is not None:
        start_str = formats.date_format(start, "j E Y, H:i")
    end_str = ''
    if end is not None:
        end_str = formats.date_format(end, "j E Y, H:i")
    return '(' + start_str + ' - ' + end_str + ')'