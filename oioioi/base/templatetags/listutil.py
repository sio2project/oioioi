"""Template tags for working with lists.

You'll use these in templates thusly::

    {% load listutil %}
    {% for sublist in mylist|parition:"3" %}
        {% for item in mylist %}
            do something with {{ item }}
        {% endfor %}
    {% endfor %}
"""

# From: http://djangosnippets.org/snippets/6/

from django import template

register = template.Library()


@register.filter
def partition(thelist, n):
    """Break a list into ``n`` pieces. The last list may be larger than the
       rest if the list doesn't break cleanly. That is::

        >>> l = range(10)

        >>> partition(l, 2)
        [[0, 1, 2, 3, 4], [5, 6, 7, 8, 9]]

        >>> partition(l, 3)
        [[0, 1, 2, 3], [4, 5, 6], [7, 8, 9]]

        >>> partition(l, 4)
        [[0, 1, 2], [3, 4, 5], [6, 7], [8, 9]]

        >>> partition(l, 5)
        [[0, 1], [2, 3], [4, 5], [6, 7], [8, 9]]

    """
    try:
        n = int(n)
        thelist = list(thelist)
    except (ValueError, TypeError):
        return [thelist]
    p = len(thelist) / n
    num_longer = len(thelist) - p * n

    return [thelist[((p + 1) * i):((p + 1) * (i + 1))]
            for i in range(num_longer)] + \
            [thelist[(p * i + num_longer):(p * (i + 1) + num_longer)]
            for i in range(num_longer, n)]


@register.filter
def partition_horizontal(thelist, n):
    """Break a list into ``n`` peices, but "horizontally." That is,
       ``partition_horizontal(range(10), 3)`` gives::

        [[1, 2, 3],
         [4, 5, 6],
         [7, 8, 9],
         [10]]

       Clear as mud?
    """
    try:
        n = int(n)
        thelist = list(thelist)
    except (ValueError, TypeError):
        return [thelist]
    newlists = [list() for i in range(n)]
    for i, val in enumerate(thelist):
        newlists[i % n].append(val)
    return newlists
