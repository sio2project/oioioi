import math
from django import template
from oioioi.gamification.experience import Experience

LARGE_WIDGET_OUTER_RADIUS = 128
LARGE_WIDGET_INNER_RADIUS = 90
SMALL_WIDGET_OUTER_RADIUS = 32

register = template.Library()


def _experience_widget(user, size):
    exp = Experience(user)
    percentage = exp.current_experience \
                 / float(exp.required_experience_to_lvlup)

    is_big = (size == 'big')

    outer_radius = LARGE_WIDGET_OUTER_RADIUS if is_big \
                   else SMALL_WIDGET_OUTER_RADIUS

    angle = 2 * math.pi * percentage
    endX = outer_radius * math.sin(angle)
    endY = outer_radius * (1 - math.cos(angle))
    end = str(endX) + ' ' + str(endY)

    large_arc_flag = '1' if percentage > 0.5 else '0'

    center = str(outer_radius) + ' ' + str(outer_radius)
    arc_parameters = center + ' 0 ' + large_arc_flag + ' 1 ' + end

    return {'percentage': percentage,
            'level': exp.current_level,
            'inner_radius': LARGE_WIDGET_INNER_RADIUS,
            'outer_radius': outer_radius,
            'diameter': outer_radius * 2,
            'size': size,
            'arc_parameters': arc_parameters}


@register.inclusion_tag('gamification/exp-widget.svg')
def experience_widget_big(user):
    return _experience_widget(user, 'big')


@register.inclusion_tag('gamification/exp-widget.svg')
def experience_widget_small(user):
    return _experience_widget(user, 'small')


@register.assignment_tag
def widget_constants():
    return {'large_outer_radius': LARGE_WIDGET_OUTER_RADIUS,
            'large_inner_radius': LARGE_WIDGET_INNER_RADIUS,
            'small_outer_radius': SMALL_WIDGET_OUTER_RADIUS}
