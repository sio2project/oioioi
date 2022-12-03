from django.core.validators import RegexValidator
from django.db import models
from django.db.models.fields import BLANK_CHOICE_DASH, exceptions
from django.forms import ValidationError
from django.utils.encoding import smart_str
from django.utils.module_loading import import_string
from django.utils.translation import gettext_lazy as _


class DottedNameField(models.CharField):
    """A ``CharField`` designed to store dotted names of Python classes.

    The mandatory argument ``superclass`` should be the class, which
    subclasses can be stored in such fields.

    Possible choices are automatically provided to Django, if the superclass
    has an attribute ``subclasses`` listing possible subclasses.
    :cls:`oioioi.base.utils.RegisteredSubclassesBase` may be used to
    automatically build such an attribute.

    Before looking up subclasses, modules with names specified in the
    ``modules_with_subclasses`` class attribute of ``superclass`` are loaded
    from all applications registered with Django.

    Subclasses may define ``description``s, which will be shown to the users
    in auto-generated forms instead of dotted names.
    """

    description = _("Dotted name of some Python object")

    def __init__(self, superclass, *args, **kwargs):
        kwargs['max_length'] = 255
        models.CharField.__init__(self, *args, **kwargs)

        self.superclass_name = superclass
        self._superclass = superclass

    # pylint: disable=W0102
    def get_choices(
        self, include_blank=True, blank_choice=BLANK_CHOICE_DASH, limit_choices_to=None
    ):
        """
        Copied from Field and replaced self.choices with generate_choices
        to avoid circular dependency.
        """
        blank_defined = False
        _choices = self._generate_choices()
        # pylint: disable=W0125
        choices = list(_choices) if _choices else []
        named_groups = choices and isinstance(choices[0][1], (list, tuple))
        if not named_groups:
            for choice, __ in choices:
                if choice in ('', None):
                    blank_defined = True
                    break

        first_choice = blank_choice if include_blank and not blank_defined else []
        # pylint: disable=W0125
        if _choices:
            return first_choice + choices
        rel_model = self.remote_field.model
        limit_choices_to = limit_choices_to or self.get_limit_choices_to()
        if hasattr(self.remote_field, 'get_related_field'):
            lst = [
                (
                    getattr(x, self.remote_field.get_related_field().attname),
                    smart_str(x),
                )
                for x in rel_model._default_manager.complex_filter(limit_choices_to)
            ]
        else:
            lst = [
                (x._get_pk_val(), smart_str(x))
                for x in rel_model._default_manager.complex_filter(limit_choices_to)
            ]
        return first_choice + lst

    def _get_choices(self):
        try:
            return self.get_choices()
        except ImportError:
            # In Django 1.9 choices array is calculated when referenced (even in
            # models file, which caused circular dependencies. Actual choices
            # are populated in `get_choices` and `validate` via
            # `_generate_choices`.
            # The assignment below notifies django to use <select> type input in
            # admin interface.
            return (('dummy', 'Dummy'),)

    choices = property(_get_choices, lambda self, value: None)

    def validate(self, value, model_instance):
        # Our custom validation
        try:
            obj = import_string(value)
        except Exception:
            raise ValidationError(_("Object %s not found") % (value,))

        superclass = self._get_superclass()
        if not issubclass(obj, superclass):
            raise ValidationError(
                _("%(value)s is not a %(class_name)s")
                % dict(value=value, class_name=superclass.__name__)
            )

        if getattr(obj, 'abstract', False):
            raise ValidationError(
                _("%s is an abstract class and cannot be used") % (value,)
            )

        # Code below copied from Field and replaced self.choices with
        # generate_choices to avoid circular dependency.
        _choices = self._generate_choices()
        if not self.editable:
            # Skip validation for non-editable fields.
            return

        if _choices and value not in self.empty_values:
            for option_key, option_value in _choices:
                if isinstance(option_value, (list, tuple)):
                    # This is an optgroup, so look inside the group for
                    # options.
                    # pylint: disable=W0612
                    for optgroup_key, optgroup_value in option_value:
                        if value == optgroup_key:
                            return
                elif value == option_key:
                    return
            raise exceptions.ValidationError(
                self.error_messages['invalid_choice'],
                code='invalid_choice',
                params={'value': value},
            )

        if value is None and not self.null:
            raise exceptions.ValidationError(self.error_messages['null'], code='null')

        if not self.blank and value in self.empty_values:
            raise exceptions.ValidationError(self.error_messages['blank'], code='blank')

    def _get_superclass(self):
        if isinstance(self._superclass, str):
            self._superclass = import_string(self._superclass)
        return self._superclass

    def _generate_choices(self):
        superclass = self._get_superclass()
        superclass.load_subclasses()
        subclasses = superclass.subclasses
        if subclasses:
            for subclass in subclasses:
                dotted_name = '%s.%s' % (subclass.__module__, subclass.__name__)
                human_readable_name = getattr(subclass, 'description', dotted_name)
                yield dotted_name, human_readable_name

    def to_python(self, value):
        superclass = self._get_superclass()
        superclass.load_subclasses()
        return super(DottedNameField, self).to_python(value)

    def deconstruct(self):
        name, path, args, kwargs = super(DottedNameField, self).deconstruct()
        kwargs['superclass'] = self.superclass_name
        del kwargs['max_length']
        return name, path, args, kwargs


class EnumRegistry(object):
    def __init__(self, max_length=64, entries=None):
        self.entries = []
        self.max_length = max_length

        if entries:
            for value, description in entries:
                self.register(value, description)

    def __iter__(self):
        return self.entries.__iter__()

    def __getitem__(self, key):
        for (val, desc) in self:
            if val == key:
                return desc
        raise KeyError(key)

    def register(self, value, description):
        if len(value) > self.max_length:
            raise ValueError(
                'Enum values must not be longer than %d chars' % (self.max_length,)
            )
        if not self.entries or value not in next(zip(*self.entries)):
            self.entries.append((value, description))

    def get(self, value, fallback):
        """Return description for a given value, or fallback if value not in
        registry"""
        for (val, desc) in self:
            if val == value:
                return desc
        return fallback


class EnumField(models.CharField):
    """A ``CharField`` designed to store a value from an extensible set.

    The set of possible values is stored in an :cls:`EnumRegistry`, which
    must be passed to the constructor.

    Other apps may then extend the set of available choices by calling
    :meth:`EnumRegistry.register`. The list of choices is populated the
    first time it is needed, therefore other application should probably
    register their values early during initialization, preferably in their
    ``models.py``.
    """

    description = _("Enumeration")

    def __init__(self, registry=None, *args, **kwargs):
        if registry:
            # This allows this field to be stored for migration purposes
            # without the need to serialize an EnumRegistry object.
            # Instead, we serialize 'max_length' and 'choices'.
            assert isinstance(
                registry, EnumRegistry
            ), 'Invalid registry passed to EnumField.__init__: %r' % (registry,)
            kwargs['max_length'] = registry.max_length
            kwargs['choices'] = self._generate_choices()
        self.registry = registry
        models.CharField.__init__(self, *args, **kwargs)

    def _generate_choices(self):
        for item in self.registry.entries:
            yield item

    def deconstruct(self):
        name, path, args, kwargs = super(EnumField, self).deconstruct()
        kwargs.pop('choices', None)
        return name, path, args, kwargs

    # Choices are made into a property so they are always fetched updated
    @property
    def choices(self):
        if self.registry:
            return self._generate_choices()
        return []

    @choices.setter
    def choices(self, new_choices):
        pass


class PhoneNumberField(models.CharField):
    """A ``CharField`` designed to store phone numbers."""

    def __init__(self, *args, **kwargs):
        kwargs['max_length'] = 64
        kwargs['validators'] = [
            RegexValidator(r'^\+?[0-9() -]{6,}$', _("Invalid phone number"))
        ]
        kwargs['help_text'] = _("Including the area code.")

        super(PhoneNumberField, self).__init__(*args, **kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super(PhoneNumberField, self).deconstruct()
        del kwargs['max_length']
        del kwargs['validators']
        del kwargs['help_text']
        return name, path, args, kwargs


class PostalCodeField(models.CharField):
    """A ``CharField`` designed to store postal codes."""

    def __init__(self, *args, **kwargs):
        kwargs['max_length'] = 6
        kwargs['validators'] = [
            RegexValidator(
                r'^\d{2}-\d{3}$', _("Enter a postal code in the format XX-XXX")
            )
        ]

        super(PostalCodeField, self).__init__(*args, **kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super(PostalCodeField, self).deconstruct()
        del kwargs['max_length']
        del kwargs['validators']
        return name, path, args, kwargs
