from django.core.urlresolvers import reverse
from django.forms.util import flatatt
from django.shortcuts import redirect
from django.template import Template, Context
from django.utils.html import conditional_escape
from django.utils.http import is_safe_url
from django.utils.safestring import mark_safe
from django.utils.encoding import force_unicode
from django.utils.importlib import import_module
import functools
import itertools
from contextlib import contextmanager
import tempfile
import shutil
import traceback
import re

# Metaclasses

class ClassInitMeta(type):
    """Meta class triggering __classinit__ on class intialization."""
    def __init__(cls, class_name, bases, new_attrs):
        super(ClassInitMeta, cls).__init__(class_name, bases, new_attrs)
        cls.__classinit__()

class ClassInitBase(object):
    """Abstract base class injecting ClassInitMeta meta class."""

    __metaclass__ = ClassInitMeta

    @classmethod
    def __classinit__(cls):
        """
            Empty __classinit__ implementation.

            This must be a no-op as subclasses can't reliably call base class's
            __classinit__ from their __classinit__s.

            Subclasses of __classinit__ should look like:

            .. python::

                class MyClass(ClassInitBase):

                    @classmethod
                    def __classinit__(cls):
                        # Need globals().get as MyClass may be still undefined.
                        super(globals().get('MyClass', cls),
                                cls).__classinit__()
                        ...

                class Derived(MyClass):

                    @classmethod
                    def __classinit__(cls):
                        super(globals().get('Derived', cls),
                                cls).__classinit__()
                        ...
        """
        pass

class RegisteredSubclassesBase(ClassInitBase):
    """A base class for classes which should have a list of subclasses
       available.

       The list of subclasses is available in their :attr:`subclasses` class
       attributes. Classes which have *explicitly* set :attr:`abstract` class
       attribute to ``True`` are not added to :attr:`subclasses`.

       If a class has ``modules_with_subclasses`` attribute (list or string),
       then specified modules for all installed applications can be loaded by
       calling :meth:`~RegisteredSubclassesBase.load_subclasses`.
    """

    _subclasses_loaded = False

    @classmethod
    def __classinit__(cls):
        this_cls = globals().get('RegisteredSubclassesBase', cls)
        super(this_cls, cls).__classinit__()
        if this_cls is cls:
            # This is RegisteredSubclassesBase class.
            return

        assert 'subclasses' not in cls.__dict__, \
                '%s defines attribute subclasses, but has ' \
                'RegisteredSubclassesMeta metaclass' % (cls,)
        cls.subclasses = []
        cls.abstract = cls.__dict__.get('abstract', False)

        def find_superclass(cls):
            superclasses = [c for c in cls.__bases__ if issubclass(c, this_cls)]
            if not superclasses:
                return None
            if len(superclasses) > 1:
                raise AssertionError('%s derives from more than one '
                        'RegisteredSubclassesBase' % (cls.__name__,))
            return superclasses[0]

        # Add the class to all superclasses' 'subclasses' attribute, including
        # self.
        superclass = cls
        while superclass is not this_cls:
            if not cls.abstract:
                superclass.subclasses.append(cls)
            superclass = find_superclass(superclass)

    @classmethod
    def load_subclasses(cls):
        if cls._subclasses_loaded:
            return
        from django.conf import settings
        modules_to_load = getattr(cls, 'modules_with_subclasses', [])
        if isinstance(modules_to_load, basestring):
            modules_to_load = [modules_to_load]
        for app_module in list(settings.INSTALLED_APPS):
            for name in modules_to_load:
                try:
                    module = '%s.%s' % (app_module, name)
                    import_module(module)
                except ImportError:
                    continue
        cls._subclasses_loaded = True

class _RemoveMixinsFromInitMixin(object):
    def __init__(self, *args, **kwargs):
        kwargs.pop('mixins', None)
        super(_RemoveMixinsFromInitMixin, self).__init__(*args, **kwargs)

class ObjectWithMixins(ClassInitBase):
    """Base class for objects which support mixins.

       Mixins are `nice tools in Python
       <http://stackoverflow.com/questions/533631/what-is-a-mixin-and-why-are-they-useful>`_.
       But they have one drawback -- you have to specify new class' mixins at
       the point where you declare it. This class solves this problem. Mixins
       can be now be added on the fly by :meth:`~ObjectWithMixins.mix_in`
       method. This allows for a more flexible modular design.

       For example::

           # base.py
           class UserController(ObjectWithMixins):
               def render_user_info(self, user):
                   return "Login: " + user.username

           # some_external_module.py
           class UserControllerBeautifier(object):
               def render_user_info(self, user):
                   super_info = super(UserControllerBeautifier, self).render_user_info(user)
                   return '<font color="red">' + super_info + '</font>'
           UserController.mix_in(UserControllerBeautifier)

       Mixins can also be specified by providing a :attr:`mixins` class
       attribute or by passing an additional keyword argument ``mixins`` to the
       constructor.

       A class with a mixin behave as if it was replaced with a subclass
       which bases are the mixin and the original class.

       The actual class with the mixins is created when the constructor is
       called or a subclass defined. Mixing in a new mixin to a class which
       have instances has an undefined effect on them.
    """

    #
    # Well, developers deserve some information on how this is implemented...
    #
    # Let's begin with a definition.
    #
    #   Let C be a class with mixins. Then the MX-class of C, denoted by MX(C),
    #   is a class which derives from C and its mixins, like this:
    #
    #     class MX_of_C(Mixin1, Mixin2, Mixin3, C):
    #         pass
    #
    # So... first imagine a clean class hierarchy without any mixins. Then
    # someone adds a mixin to class C. Two things may happen:
    #
    #  1. If C has no subclasses, the new mixin is only added to C.mixins.
    #
    #  2. If C has subclasses S_i, they are also modified by replacing C
    #     in S_i.__bases__ with MX(C).
    #
    # If a new subclass S of C is later created, S.__bases__ is
    # immediately altered to contain MX(C) instead of C.
    #
    # If a new instance of C is requested, an instance of MX(C) is returned
    # instead (see ObjectWithMixins.__new__). It works similarly if the 'mixin'
    # keyword argument is passed to the constructor --- then a temporary
    # MX-class is created and instantiated.
    #

    #: A list of mixins to be automatically mixed in to all instances of the
    #: particular class and its subclasses.
    mixins = []

    #: Setting this to ``True`` allows adding mixins to the class after it has
    #: been instantiated. Existing instances will not have new mixins added.
    allow_too_late_mixins = False

    @classmethod
    def __classinit__(cls):
        this_cls = globals().get('ObjectWithMixins', cls)
        super(this_cls, cls).__classinit__()
        if this_cls is cls:
            # This is ObjectWithMixins class.
            return
        if '__unmixed_class__' in cls.__dict__:
            # This is an artificially created class with mixins already
            # applied.
            return
        cls._mx_class = None
        cls._direct_subclasses = []
        cls.__unmixed_class__ = cls
        cls.mixins = cls.__dict__.get('mixins', [])
        for base in cls.__bases__:
            if issubclass(base, this_cls) and base is not this_cls:
                base.__unmixed_class__._direct_subclasses.append(cls)
                base.__unmixed_class__._fixup_subclass(cls)

    def __new__(cls, *args, **kwargs):
        for c in cls.__mro__:
            if issubclass(c, ObjectWithMixins):
                c._has_instances = True
        if 'mixins' in kwargs:
            mixins = [_RemoveMixinsFromInitMixin] + list(kwargs['mixins'])
        else:
            mixins = []
        mixins.extend(cls.mixins)
        return object.__new__(cls._make_mx_class(mixins))

    @classmethod
    def _make_mx_class(cls, mixins):
        if mixins:
            bases = tuple(mixins) + (cls,)
            return type(cls.__name__ + 'WithMixins', bases,
                    dict(__module__=cls.__module__, __unmixed_class__=cls))
        else:
            return cls

    @classmethod
    def _get_mx_class(cls):
        if cls._mx_class:
            return cls._mx_class
        assert cls.__unmixed_class__ is cls
        cls_with_mixins = cls._make_mx_class(cls.mixins)
        cls._mx_class = cls_with_mixins
        return cls_with_mixins

    @classmethod
    def _fixup_subclasses(cls):
        assert cls.__unmixed_class__ is cls
        for subclass in cls._direct_subclasses:
            cls._fixup_subclass(subclass)

    @classmethod
    def _fixup_subclass(cls, subclass):
        assert cls.__unmixed_class__ is cls
        cls_with_mixins = cls._get_mx_class()
        new_bases = []
        for base in subclass.__bases__:
            if base.__unmixed_class__ is cls:
                new_bases.append(cls_with_mixins)
            else:
                new_bases.append(base)
        subclass.__bases__ = tuple(new_bases)

    @classmethod
    def mix_in(cls, mixin):
        """Appends the given mixin to the list of class mixins."""
        assert cls.__unmixed_class__ is cls
        assert cls.allow_too_late_mixins or \
                '_has_instances' not in cls.__dict__, \
                "Adding mixin %r to %r too late. The latter already has " \
                "instances." % (mixin, cls)
        cls.mixins.append(mixin)
        cls._mx_class = None
        cls._fixup_subclasses()

# Memoized-related bits copied from SqlAlchemy.

class memoized_property(object):   # Copied from SqlAlchemy
    """A read-only @property that is only evaluated once."""
    def __init__(self, fget, doc=None):
        self.fget = fget
        self.__doc__ = doc or fget.__doc__
        self.__name__ = fget.__name__

    def __get__(self, obj, cls):
        if obj is None:
            return None
        obj.__dict__[self.__name__] = result = self.fget(obj)
        return result

def memoized(fn):
    """Simple wrapper that adds result caching for functions with positional
       arguments only.

       The arguments must be hashable so that they can be stored as keys in
       a dict.
    """
    cache = {}
    @functools.wraps(fn)
    def memoizer(*args):
        if args not in cache:
            cache[args] = fn(*args)
        return cache[args]
    memoizer.cache = cache
    return memoizer

def reset_memoized(memoized_fn):
    """Clear the memoization cache of a function decorated by
       :fun:`memoized`."""
    memoized_fn.cache.clear()

# Finding objects by name

def request_cached(fn):
    """Adds per-request caching for functions which operate on sole request."""
    @functools.wraps(fn)
    def cacher(request):
        if not hasattr(request, '_cache'):
            setattr(request, '_cache', {})
        if fn not in request._cache:
            request._cache[fn] = fn(request)
        return request._cache[fn]
    return cacher

@memoized
def get_object_by_dotted_name(name):
    """Returns an object by its dotted name, e.g.
       ``oioioi.base.utils.get_object_by_dotted_name``."""
    if '.' not in name:
        raise AssertionError('Invalid object name: %s' % (name,))
    module, obj = name.rsplit('.', 1)
    try:
        return getattr(__import__(module, fromlist=[obj]), obj)
    except AttributeError, e:
        raise ImportError('Requested object %r not found: %s' % (name, e))

# Generating HTML

def make_html_link(href, name, extra_attrs={}):
    attrs = {'href': href}
    attrs.update(extra_attrs)
    return mark_safe(u'<a %s>%s</a>' % (flatatt(attrs),
            conditional_escape(force_unicode(name))))

def make_html_links(links, extra_attrs={}):
    links = [make_html_link(href, name, extra_attrs) for href, name in links]
    return mark_safe(' | '.join(links))

def make_navbar_badge(link, text):
    template = Template('<li><a href="{{ link }}"><span class="label '
            'label-important">{{ text }}</span></a></li>')
    return template.render(Context({'link': link, 'text': text}))

# Redirects

def safe_redirect(request, url, fallback='index'):
    if url and is_safe_url(url=url, host=request.get_host()):
        next_page = url
    else:
        next_page = reverse(fallback)

    return redirect(next_page)

# File uploads

@contextmanager
def uploaded_file_name(uploaded_file):
    if hasattr(uploaded_file, 'temporary_file_path'):
        yield uploaded_file.temporary_file_path()
    else:
        f = tempfile.NamedTemporaryFile(suffix=uploaded_file.name)
        shutil.copyfileobj(uploaded_file, f)
        f.flush()
        yield f.name
        f.close()

# Natural sort key

def naturalsort_key(key):
    convert = lambda text: int(text) if text.isdigit() else text
    return [ convert(c) for c in re.split('([0-9]+)', key) ]

