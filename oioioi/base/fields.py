from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.forms import ValidationError
from django.core.validators import RegexValidator
from oioioi.base.utils import get_object_by_dotted_name


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

    __metaclass__ = models.SubfieldBase

    def __init__(self, superclass, *args, **kwargs):
        kwargs['max_length'] = 255
        kwargs['choices'] = self._generate_choices()
        models.CharField.__init__(self, *args, **kwargs)

        self.superclass_name = superclass
        self._superclass = superclass

    def _get_superclass(self):
        if isinstance(self._superclass, basestring):
            self._superclass = get_object_by_dotted_name(self._superclass)
        return self._superclass

    def _generate_choices(self):
        superclass = self._get_superclass()
        superclass.load_subclasses()
        subclasses = superclass.subclasses
        if subclasses:
            for subclass in subclasses:
                dotted_name = '%s.%s' % (subclass.__module__,
                        subclass.__name__)
                human_readable_name = getattr(subclass, 'description',
                        dotted_name)
                yield dotted_name, human_readable_name

    def to_python(self, value):
        superclass = self._get_superclass()
        superclass.load_subclasses()
        return super(DottedNameField, self).to_python(value)

    def validate(self, value, model_instance):
        try:
            obj = get_object_by_dotted_name(value)
        except Exception:
            raise ValidationError(_("Object %s not found") % (value,))

        superclass = self._get_superclass()
        if not issubclass(obj, superclass):
            raise ValidationError(_("%(value)s is not a %(class_name)s")
                    % dict(value=value, class_name=superclass.__name__))

        if getattr(obj, 'abstract', False):
            raise ValidationError(_("%s is an abstract class and cannot be "
                "used") % (value,))

    def deconstruct(self):
        name, path, args, kwargs = super(DottedNameField, self).deconstruct()
        kwargs['superclass'] = self.superclass_name
        del kwargs['max_length']
        return name, path, args, kwargs


class EnumRegistry(object):
    def __init__(self, max_length=64):
        self.entries = []
        self.max_length = max_length

    def __iter__(self):
        return self.entries.__iter__()

    def __getitem__(self, key):
        for (val, desc) in self:
            if val == key:
                return desc
        raise KeyError(key)

    def register(self, value, description):
        if len(value) > self.max_length:
            raise ValueError('Enum values must not be longer than %d chars' %
                    (self.max_length,))
        if not self.entries or value not in zip(*self.entries)[0]:
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
            assert isinstance(registry, EnumRegistry), \
                    'Invalid registry passed to EnumField.__init__: %r' % \
                    (registry,)
            kwargs['max_length'] = registry.max_length
            kwargs['choices'] = self._generate_choices()
        models.CharField.__init__(self, *args, **kwargs)
        self.registry = registry

    def _generate_choices(self):
        for item in self.registry.entries:
            yield item


class PhoneNumberField(models.CharField):
    """A ``CharField`` designed to store phone numbers."""

    def __init__(self, *args, **kwargs):
        kwargs['max_length'] = 64
        kwargs['validators'] = [RegexValidator(r'^\+?[0-9() -]{6,}$',
                                              _("Invalid phone number"))]
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
        kwargs['validators'] = [RegexValidator(r'^\d{2}-\d{3}$',
                               _("Enter a postal code in the format XX-XXX"))]

        super(PostalCodeField, self).__init__(*args, **kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super(PostalCodeField, self).deconstruct()
        del kwargs['max_length']
        del kwargs['validators']
        return name, path, args, kwargs
