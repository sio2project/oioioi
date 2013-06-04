""" Translate OK, WA, etc. into numbers for XML ranking.

    Usage:
    {{ x|xmlreport_result }}

"""

from django import template

register = template.Library()


@register.filter
def xmlreport_result(x):
    repls = {
        'OK': '1',
        'WA': '2',
        'TLE': '3',  # also 15
        # 4 stands for 'no answer'
        'RE': '5',
        'SV': '6',
        # 7 stands for 'not telling'
    }
    if x in repls:
        return repls[x]
    return '0'
