# pylint: disable=bad-super-call
import base64
import functools
import json
import os
import re
import shutil
import sys
import tempfile
from contextlib import contextmanager
from importlib import import_module

import six
import urllib.parse
from django.forms.utils import flatatt
from django.http import Http404, HttpResponse, HttpResponseRedirect
from django.shortcuts import render
from django.template import Template
from django.template.loader import render_to_string
from django.template.response import TemplateResponse
from django.utils.encoding import force_str
from django.utils.html import conditional_escape
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _

# Metaclasses


class ClassInitMeta(type):
    """Meta class triggering __classinit__ on class intialization."""

    def __init__(cls, class_name, bases, new_attrs):
        super(ClassInitMeta, cls).__init__(class_name, bases, new_attrs)
        cls.__classinit__()


class ClassInitBase(object, metaclass=ClassInitMeta):
    """Abstract base class injecting ClassInitMeta meta class."""

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

        if '__unmixed_class__' in cls.__dict__ and cls.__unmixed_class__ is not cls:
            # This is an artificial class created by mixins mechanism
            return

        assert 'subclasses' not in cls.__dict__, (
            '%s defines attribute subclasses, but has '
            'RegisteredSubclassesMeta metaclass' % (cls,)
        )
        cls.subclasses = []
        cls.abstract = cls.__dict__.get('abstract', False)

        def find_superclass(cls):
            superclasses = [c for c in cls.__bases__ if issubclass(c, this_cls)]
            if not superclasses:
                return None
            if len(superclasses) > 1:
                raise AssertionError(
                    '%s derives from more than one '
                    'RegisteredSubclassesBase' % (cls.__name__,)
                )
            superclass = superclasses[0]
            if '__unmixed_class__' in superclass.__dict__:
                superclass = superclass.__unmixed_class__
            return superclass

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
        if isinstance(modules_to_load, str):
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
                   super_info = super(UserControllerBeautifier, self) \
                                .render_user_info(user)
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
            return type(
                cls.__name__ + 'WithMixins',
                bases,
                dict(__module__=cls.__module__, __unmixed_class__=cls),
            )
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
        assert (
            cls.allow_too_late_mixins or '_has_instances' not in cls.__dict__
        ), "Adding mixin %r to %r too late. The latter already has instances." % (
            mixin,
            cls,
        )
        cls.mixins.append(mixin)
        cls._mx_class = None
        cls._fixup_subclasses()


# Memoized-related bits copied from SqlAlchemy.


class memoized_property(object):  # Copied from SqlAlchemy
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


def request_cached_complex(fn):
    """Adds per-request caching for functions which operate on more than a request.
    Additional arguments and keyword arguments passed to the wrapped function
    must be hashable, which generally means that their type must be immutable.
    """

    @functools.wraps(fn)
    def cacher(request, *args, **kwargs):
        if not hasattr(request, '_cache'):
            setattr(request, '_cache', {})
        key = (fn, tuple(args), tuple(kwargs.items()))
        if key not in request._cache:
            request._cache[key] = fn(request, *args, **kwargs)
        return request._cache[key]

    return cacher


# Generating HTML


def make_html_link(href, name, method='GET', extra_attrs=None):
    if method == 'GET':
        attrs = {'href': href}
    elif method == 'POST':
        attrs = {'data-post-url': href, 'href': '#'}
    if not extra_attrs:
        extra_attrs = {}
    attrs.update(extra_attrs)
    return mark_safe(
        u'<a %s>%s</a>' % (flatatt(attrs), conditional_escape(force_str(name)))
    )


def make_html_links(links, extra_attrs=None):
    if not extra_attrs:
        extra_attrs = {}
    html_links = []
    for link in links:
        html_links.append(make_html_link(*link, extra_attrs=extra_attrs))
    return mark_safe(' | '.join(html_links))


def make_navbar_badge(link, text, id=None):
    if link is not None or text is not None:
        return render_to_string(
            'utils/navbar-badge.html', context={'link': link, 'text': text, 'id': id}
        )
    return ""


# Creating views


def tabbed_view(request, template, context, tabs, tab_kwargs, link_builder):
    """A framework for building pages that are split into tabs.

    The current tab is picked using the 'key' GET parameter.
    The given template is rendered using the given context, which is
    extended by 'current_tab', representing the opened tab, 'tabs',
    a set of 'obj' and 'link' pairs for each existing tab, where 'obj'
    represents the tab and 'link' is a link to the tab's page,
    and 'content', the tab's rendered content.

    :param request: a HttpRequest object given to the view
    :param template: the rendered template
    :param context: additional context to be passed to the template
    :param tabs: an iterable of tabs. Each tab must have a unique 'key'
            attribute that will be used to create an URL to the tab,
            a 'view' attribute returning either HttpResponseRedirect,
            TemplateResponse or rendered html, and an optional 'condition'
            attribute: a function taking a request and returning
            if the tab should be accessible for this request. If there is
            no condition then it is assumed to be always returning True.
    :param tab_kwargs: a dict to be passed as kwargs to each tab's view
    :param link_builder: a function which receives a tab and returns
            a link to the tab. It should contain a proper path
            and the appropriate 'key' parameter.
    """
    tabs = [
        t
        for t in tabs
        if not hasattr(t, 'condition')
        or 'problem' not in context
        or t.condition(request, context['problem'])
    ]
    if 'key' not in request.GET:
        if not tabs:
            raise Http404
        qs = request.GET.dict()
        qs['key'] = next(iter(tabs)).key
        return HttpResponseRedirect(
            request.path + '?' + urllib.parse.urlencode(qs)
        )
    key = request.GET['key']
    for tab in tabs:
        if tab.key == key:
            current_tab = tab
            break
    else:
        raise Http404

    response = current_tab.view(request, **tab_kwargs)
    if isinstance(response, HttpResponseRedirect):
        return response

    if isinstance(response, TemplateResponse):
        content = response.render().content
    else:
        content = response

    tabs_context = [{'obj': tab, 'link': link_builder(tab)} for tab in tabs]
    context.update(
        {
            'current_tab': current_tab,
            'tabs': tabs_context,
            'content': mark_safe(force_str(content)),
        }
    )
    return TemplateResponse(request, template, context)


# Other utils


@contextmanager
def uploaded_file_name(uploaded_file):
    if hasattr(uploaded_file, 'temporary_file_path'):
        yield uploaded_file.temporary_file_path()
    else:
        f = tempfile.NamedTemporaryFile(suffix=os.path.basename(uploaded_file.name))
        shutil.copyfileobj(uploaded_file, f)
        f.flush()
        yield f.name
        f.close()


def split_extension(filename):
    special_extensions = ['.tar.gz', '.tar.bz2', '.tar.xz']
    for ext in special_extensions:
        if filename.endswith(ext):
            return (filename.rstrip(ext), ext)
    return os.path.splitext(filename)


# https://docs.djangoproject.com/en/1.8/ref/files/storage/#django.core.files.storage.Storage.get_available_name
_STRIP_NUM_RE = re.compile(r'^(.*)_\d+$')
_STRIP_HASH_RE = re.compile(r'^(.*)_[a-zA-Z0-9]{7}$')


def strip_num_or_hash(filename):
    name, ext = split_extension(filename)
    new_name = name
    m = _STRIP_NUM_RE.match(name)
    if m:
        new_name = m.group(1)
    m = _STRIP_HASH_RE.match(name)
    if m:
        new_name = m.group(1)
    return new_name + ext


def naturalsort_key(key):
    convert = lambda text: int(text) if text.isdigit() else text
    return [convert(c) for c in re.split('([0-9]+)', key)]


class ProgressBar(object):
    """Displays simple textual progress bar."""

    def __init__(self, max_value, length=20):
        self.max_value = max_value
        self.value = 0
        self.to_clear = 0
        self.length = length

    def _show(self, preserve=False):
        done_p = 100 * self.value / self.max_value
        done_l = self.length * self.value / self.max_value
        s = '|' + '=' * done_l + ' ' * (self.length - done_l) + '|  %d%%' % done_p
        self.to_clear = 0 if preserve else len(s)
        sys.stdout.write(s + ('\n' if preserve else ''))
        sys.stdout.flush()

    def _clear(self):
        if self.to_clear:
            sys.stdout.write('\b' * self.to_clear)
            sys.stdout.flush()

    def update(self, value=None, preserve=False):
        """Set new value (if given) and redraw the bar.

        :param preserve: controls if bar will end with a new line and
                         stay after next update.
        """
        if value:
            if value > self.max_value:
                raise ValueError(_("Too large value for progress bar"))
            self.value = value
        if sys.stdout.isatty():
            self._clear()
            self._show(preserve)
        elif preserve:
            self._show(preserve)


def jsonify(view):
    """A decorator to serialize view result with JSON.

    The object returned by ``view`` will be converted to JSON and returned
    as an appropriate :class:`django.http.HttpResponse`.
    """

    @functools.wraps(view)
    def inner(*args, **kwargs):
        data = view(*args, **kwargs)
        return HttpResponse(json.dumps(data), content_type='application/json')

    return inner


def add_header(header, value):
    def decorator(view):
        @functools.wraps(view)
        def inner(*args, **kwargs):
            response = view(*args, **kwargs)
            response[header] = value
            return response

        return inner

    return decorator


def allow_cross_origin(arg='*'):
    """Add Access-Control-Allow-Origin header with given value,
    or '*' if none given.

    May be used as any of:

    @allow_cross_origin
    @allow_cross_origin()
    @allow_cross_origin('http://example.com')
    """
    if callable(arg):
        return allow_cross_origin()(arg)
    return add_header('Access-Control-Allow-Origin', arg)


def is_ajax(request):
    """Check if 'request' is an jQuery AJAX call."""
    return request.headers.get('x-requested-with') == 'XMLHttpRequest'


def generate_key():
    """Generate an random key, encoded in url-safe way."""
    # 18 bytes = 144 bits of entropy, 24 bytes in base64.
    return six.ensure_text(base64.urlsafe_b64encode(os.urandom(18)))


# User-related


def get_user_display_name(user):
    """This method returns the full user name if available and
    the username otherwise.
    """
    return user.get_full_name() or user.username


# Miscellaneous


def find_closure(groups):
    """Finds closure of sets.

    If any two elements were within same input set,they will be in
    one unique set in the output.

    >>> find_closure([[1, 2], [2, 3], [4]])
    [[1, 2, 3], [4],]
    """
    parent = {}

    def find(elem):
        if parent[elem] != elem:
            parent[elem] = find(parent[elem])
        return parent[elem]

    def union(elem1, elem2):
        parent[find(elem1)] = find(elem2)

    for group in groups:
        for elem in group:
            parent.setdefault(elem, elem)
            union(elem, group[0])
    new_groups = {}
    for elem in parent.keys():
        new_groups.setdefault(find(elem), []).append(elem)
    return list(new_groups.values())
