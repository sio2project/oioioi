"""Template tags for working with lists."""

from django import template

register = template.Library()


@register.filter
def partition(thelist, n):
    """
    From: http://djangosnippets.org/snippets/6/

    Break a list into ``n`` pieces. If ``n`` is not a divisor of the
    length of the list, then first pieces are one element longer
    then the last ones. That is::

    >>> l = range(10)

    >>> partition(l, 2)
    [[0, 1, 2, 3, 4], [5, 6, 7, 8, 9]]

    >>> partition(l, 3)
    [[0, 1, 2, 3], [4, 5, 6], [7, 8, 9]]

    >>> partition(l, 4)
    [[0, 1, 2], [3, 4, 5], [6, 7], [8, 9]]

    >>> partition(l, 5)
    [[0, 1], [2, 3], [4, 5], [6, 7], [8, 9]]

    You can use the filter in the following way:

        {% load listutil %}
        {% for sublist in mylist|parition:"3" %}
            {% for item in sublist %}
                do something with {{ item }}
            {% endfor %}
        {% endfor %}
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
def cyclic_lookup(thelist, index):
    return thelist[index % len(thelist)]
