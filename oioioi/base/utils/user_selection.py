import django
from django import forms
from django.conf import settings
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.http import Http404
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _
from oioioi.base.utils import jsonify

INVALID_USER_SELECTION = '__invalid_user_selection__'


def _prefix(user_field_name, q_field):
    if user_field_name is None:
        return q_field
    else:
        return user_field_name + '__' + q_field


def _get_user_q_expression(substr, user_field_name=None):
    # Returns a Q expression which matches the given user
    # input (substr) to a ForeignKey field named user_field_name
    # (or directly to the User model if user_field_name is None).

    substr = substr.split()

    if len(substr) > 2:
        q_dict = {
            _prefix(user_field_name, 'first_name__icontains'): ' '.join(substr[:-1]),
            _prefix(user_field_name, 'last_name__icontains'): substr[-1],
        }
        q_expression = Q(**q_dict)
    elif len(substr) == 2:
        q_dict_first_last = {
            _prefix(user_field_name, 'first_name__icontains'): substr[0],
            _prefix(user_field_name, 'last_name__icontains'): substr[1],
        }
        q_dict_two_first = {
            _prefix(user_field_name, 'first_name__icontains'): ' '.join(substr)
        }
        q_expression = Q(**q_dict_first_last) | Q(**q_dict_two_first)
    else:
        q_dict_username = {_prefix(user_field_name, 'username__icontains'): substr[0]}
        q_dict_first = {_prefix(user_field_name, 'first_name__icontains'): substr[0]}
        q_dict_last = {_prefix(user_field_name, 'last_name__icontains'): substr[0]}
        q_expression = Q(**q_dict_username) | Q(**q_dict_first) | Q(**q_dict_last)

    return q_expression


def _get_user_hints(substr, queryset, user_field_name=None):
    if substr is None:
        return None
    substr = str(substr)
    if len(substr) < 2:
        return None
    q_expression = _get_user_q_expression(substr, user_field_name)
    if user_field_name is not None:
        queryset = queryset.order_by(user_field_name)
    num_hints = getattr(settings, 'NUM_HINTS', 10)
    users = (
        queryset.filter(q_expression)
        .distinct()
        .values_list(
            _prefix(user_field_name, 'username'),
            _prefix(user_field_name, 'first_name'),
            _prefix(user_field_name, 'last_name'),
        )
    )
    return ['%s (%s %s)' % u for u in users[:num_hints]]


@jsonify
def get_user_hints_view(
    request, request_field_name, queryset=None, user_field_name=None
):
    user_hints = _get_user_hints(
        request.GET.get(request_field_name, ''), queryset, user_field_name
    )
    if user_hints is None:
        raise Http404
    return user_hints


def _parse_user_hint(value, queryset=None, user_field_name=None):
    assert queryset is not None or user_field_name is None

    if queryset is None:
        queryset = User.objects.all()

    value = value.split()

    if len(value) == 1 or (
        len(value) > 1 and value[1].startswith('(') and value[-1].endswith(')')
    ):

        value = value[0]

        try:
            queryset = queryset.filter(**{_prefix(user_field_name, 'username'): value})
            if not queryset:
                return None
            return User.objects.get(username=value)
        except User.DoesNotExist:
            return None
    else:
        return None


class UserSelectionWidget(forms.TextInput):
    html_template = (
        "<script>init_user_selection('%(id)s', %(num_hints)s)</script>"
    )

    def __init__(self, attrs=None):
        if attrs is None:
            attrs = {}
        else:
            attrs = dict(attrs)
        attrs.setdefault('autocomplete', 'off')
        super(UserSelectionWidget, self).__init__(attrs)

    def render(self, name, value, attrs=None, renderer=None):
        html = super(UserSelectionWidget, self).render(name, value, attrs, renderer)
        html += mark_safe(
            self.html_template
            % {
                'id': attrs['id'],
                'num_hints': getattr(settings, 'NUM_HINTS', 10),
            }
        )
        return html


class UserSelectionField(forms.CharField):
    widget = UserSelectionWidget

    def __init__(self, hints_url=None, queryset=None, user_field_name=None, **kwargs):
        super(UserSelectionField, self).__init__(**kwargs)
        self.hints_url = hints_url
        self.queryset = queryset
        self.user_field_name = user_field_name

    @property
    def hints_url(self):
        return self.widget.attrs.get('data-hints-url')

    @hints_url.setter
    def hints_url(self, value):
        self.widget.attrs['data-hints-url'] = value

    def prepare_value(self, value):
        if isinstance(value, User):
            return value.username
        if isinstance(value, int):
            try:
                return User.objects.get(id=value).username
            except User.DoesNotExist:
                pass
        return super(UserSelectionField, self).prepare_value(value)

    def to_python(self, value):
        value = super(UserSelectionField, self).to_python(value)
        if isinstance(value, User):
            user = value
        else:
            user = _parse_user_hint(value, self.queryset, self.user_field_name)
            if value and not user:
                raise ValidationError(
                    _(
                        "User not found or you do not have "
                        "access to this user account: %s"
                    )
                    % (value,)
                )
        return user
