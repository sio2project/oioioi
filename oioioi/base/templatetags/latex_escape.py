r""" Escape string for generating LaTeX report.

    Usage:
    {{ malicious|latex_escape }}

    Remember: when generating LaTeX report, you should always check
    whether \write18 is disabled!
    http://www.texdev.net/2009/10/06/what-does-write18-mean/
"""

from django import template

register = template.Library()


@register.filter
def latex_escape(x):
    res = unicode(x)
    # Braces + backslashes
    res = res.replace('\\', '\\textbackslash\\q{}')
    res = res.replace('{', '\\{')
    res = res.replace('}', '\\}')
    res = res.replace('\\q\\{\\}', '\\q{}')
    # then everything followed by empty space
    repls = [
        ('#', '\\#'),
        ('$', '\\$'),
        ('%', '\\%'),
        ('_', '\\_'),
        ('<', '\\textless{}'),
        ('>', '\\textgreater{}'),
        ('&', '\\ampersand{}'),
        ('~', '\\textasciitilde{}'),
        ('^', '\\textasciicircum{}'),
        ('"', '\\doublequote{}'),
        ('\'', '\\singlequote{}'),
    ]

    for key, value in repls:
        res = res.replace(key, value)
    return res
