from django import template

register = template.Library()

@register.simple_tag
def format_data_range(start, end):
    if start is not None and end is not None:
        if start.year == end.year and start.month == end.month and start.day == end.day:
            day = start.strftime("%d %b %Y")
            start_str = start.strftime("%H:%M")
            end_str = end.strftime("%H:%M")
            return '(' + day + ', ' + start_str + ' - ' + end_str + ')'

    start_str = ''
    if start is not None:
        start_str = start.strftime("%d %b %Y, %H:%M")
    end_str = ''
    if end is not None:
        end_str = end.strftime("%d %b %Y, %H:%M")
    return '(' + start_str + ' - ' + end_str + ')'