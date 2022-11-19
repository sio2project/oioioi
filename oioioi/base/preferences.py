from collections import OrderedDict
from oioioi.base.models import UserPreferences

# Huge thanks to: http://jacobian.org/writing/dynamic-form-generation/
class PreferencesFactory(object):
    """Since each app might want to add new options for the user to edit in his
    preferences, this class was created - it allows for adding new fields to
    the form and requesting callback when the form will have been completed
    Usage:
    PreferencesFactory.add_field(
        "Dog",
        CharField,
        lambda name, user: 'Spot',
        max_length=20
    )

    form = PreferencesFactory().create_form(UserForm, user, allow_login_change=False)
    """

    _additional_fields = []

    @staticmethod
    def add_field(
        field_name, field_type, initial_value_callback, order=0, *args, **kwargs
    ):
        """When the user will want to edit preferences there will be additional
        field listed, as if it was specified in the form:

        class OurForm(Forms.form):
            field_name = field_type(*args, **kwargs)

        Order is an int that will be used to sort additional fields in
        ordered dict, set to 0 if you don't care

        When instating the form, initial_value_callback will be called
        with the field_name and user parameters
        initial_value_callback(field_name, user), it should return a value
        that can be put in field_type, this is what the user will see when
        opens his preferences, preferably some saved info from before.

        To actually get the results you should use the PreferencesSaved
        signal from models (and to validate use the field validators, fool)

        Keep in mind that adding fields that already exist is an
        undefined behavior.
        """
        PreferencesFactory._additional_fields.append(
            {
                'name': field_name,
                'type': field_type,
                'order': order,
                'callback': initial_value_callback,
                'args': args,
                'kwargs': kwargs,
            }
        )

    @staticmethod
    def remove_field(field_name):
        """Removes field with given name."""
        for field in PreferencesFactory._additional_fields[:]:
            if field['name'] == field_name:
                PreferencesFactory._additional_fields.remove(field)

    def create_form(self, form_class, user, *args, **kwargs):
        """Returns a form with all the additional fields which can then be
        displayed to the user, additional args and kwargs will be sent to
        the form's __init__ (instance though will be provided for you)
        """
        PreferencesFactory._additional_fields.sort(
            key=lambda o: (o["order"], o["name"])
        )
        extra_fields = OrderedDict()
        field_values = {}
        for field in PreferencesFactory._additional_fields:
            field_values[field['name']] = field['callback'](field['name'], user)
            extra_fields[field['name']] = field['type'](
                *field['args'], **field['kwargs']
            )

        # Since the user of this class might have put his own initial values we
        # need to joign them all
        initial = kwargs.pop('initial', {})
        initial.update(field_values)

        return form_class(
            *args, extra=extra_fields, instance=user, initial=initial, **kwargs
        )


def ensure_preferences_exist_for_user(user):
    if not hasattr(user, "userpreferences"):
        UserPreferences.objects.get_or_create(user=user)
