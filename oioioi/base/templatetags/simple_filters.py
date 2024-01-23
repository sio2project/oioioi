import json
import types
from copy import copy

from django import template
from django.forms import CheckboxInput, CheckboxSelectMultiple, RadioSelect
from django.utils.html import escapejs
from django.utils.safestring import mark_safe

from oioioi.contests.scores import IntegerScore
from oioioi.mp.score import FloatScore
from oioioi.pa.score import PAScore

register = template.Library()


@register.filter
def is_checkbox(field):
    return isinstance(field.field.widget, CheckboxInput)


@register.filter
def is_checkbox_select_multiple(field):
    return isinstance(field.field.widget, CheckboxSelectMultiple)


@register.filter
def is_radioselect(field):
    return isinstance(field.field.widget, RadioSelect)


@register.filter
def lookup(d, key):
    """
    Lookup value from dictionary

    Example:

    {% load simple_filters %}
    {{ dict|lookup:key }}
    """
    return d[key]


@register.filter
def safe_lookup(d, key):
    """
    Lookup value from dictionary. Returns None if key ``key``
    is not present in ``d``.

    Example:

    {% load simple_filters %}
    {{ dict|safe_lookup:key }}
    """
    return d.get(key)


@register.filter
def multival_lookup(d, key):
    """
    Returns a value list corresponding to a key from Django's MultiValueDict
    """
    return d.getlist(key)


@register.filter(name='indent')
def indent_string(value, num_spaces=4):
    """
    Adds ``num_spaces`` spaces at the
    beginning of every line in value.
    """
    return ' ' * num_spaces + value.replace('\n', '\n' + ' ' * num_spaces)


def _append_attr(field, attribute, value):
    # adapted from 'django-widget-tweaks'
    field = copy(field)
    # decorate field.as_widget method with updated attributes
    old_as_widget = field.as_widget

    def as_widget(self, widget=None, attrs=None, only_initial=False):
        widget = widget or self.field.widget
        attrs = attrs or {}

        custom_append_attr = getattr(widget, "append_attr", None)
        if not (custom_append_attr and custom_append_attr(attribute, value)):
            if attrs.get(attribute):
                attrs[attribute] += " " + value
            elif widget.attrs.get(attribute):
                attrs[attribute] = widget.attrs[attribute] + " " + value
            else:
                attrs[attribute] = value
            if attribute == "type":  # change the Input type
                self.field.widget.input_type = value
                del attrs["type"]

        html = old_as_widget(widget, attrs, only_initial)
        self.as_widget = old_as_widget
        return html

    field.as_widget = types.MethodType(as_widget, field)
    return field


@register.filter(name='add_class')
def add_class(field, css_class):
    """
    Adds css class to a django form field
    :param field: form field
    :param css_class: css class
    :return: field with added class

    Example usage

    # my_app/forms.py
    ```python
    class MyForm(Form):
        my_field = forms.CharField(max_length=100)

    # my_app/views.py
    ```python
    def get_form(request):
        my_form = MyForm()
        return render(request, 'my_form.html', { form: my_form })
    ```

    # my_app/templates/my_form.html
    ```html
    {{ form.field|add_class:"my-class" }}
    ```

    would generate

    ```html
    <input class="my-class" id="my_field" name="my_field" />
    ```
    """
    return _append_attr(field, "class", css_class)


@register.filter
def add_form(field, form_id):
    return _append_attr(field, "form", form_id)


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

        {% load simple_filters %}
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
    p = len(thelist) // n
    num_longer = len(thelist) - p * n

    return [thelist[((p + 1) * i) : ((p + 1) * (i + 1))] for i in range(num_longer)] + [
        thelist[(p * i + num_longer) : (p * (i + 1) + num_longer)]
        for i in range(num_longer, n)
    ]


@register.filter
def cyclic_lookup(thelist, index):
    return thelist[index % len(thelist)]


@register.filter(name='zip')
def zip_lists(a, b):
    return list(zip(a, b))


@register.filter
def jsonify(value):
    """
    Be careful when using it directly in js! Code like that:

    <script>
        var x = {{ some_user_data|jsonify }};
    </script>

    contains an XSS vulnerability. That's because browsers
    will interpret </script> tag inside js string.
    """
    return mark_safe(json.dumps(value))


@register.filter
def json_parse(value):
    """
    This is a correct way of embedding json inside js in an HTML template.
    """
    return mark_safe('JSON.parse(\'%s\')' % escapejs(json.dumps(value)))


@register.filter
def latex_escape(x):
    r"""
    Escape string for generating LaTeX report.

    Usage:
    {{ malicious|latex_escape }}

    Remember: when generating LaTeX report, you should always check
    whether \write18 is disabled!
    http://www.texdev.net/2009/10/06/what-does-write18-mean/
    """
    res = str(x)
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


@register.filter
def result_color_class(raw_score):
    if raw_score in [None, '']:
        return ''

    if callable(getattr(raw_score, 'to_int', None)):
        score = raw_score.to_int()
    else:
        score = int(raw_score)

    if isinstance(raw_score, IntegerScore):
        score_max_value = 100
    elif isinstance(raw_score, PAScore):
        score_max_value = 10
    elif isinstance(raw_score, FloatScore):
        score_max_value = 100
    else:
        # There should be a method to get maximum points for
        # contest, for now, support just above cases.
        return ''

    if score == 0:
        return 'submission--WA'

    score_color_threshold = 25
    buckets_count = 4
    points_per_bucket = score_max_value / float(buckets_count)

    # Round down to multiple of $score_color_threshold.
    bucket = int(score / points_per_bucket) * score_color_threshold

    return 'submission--OK{}'.format(bucket)
