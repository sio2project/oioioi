import random
import sys
import os.path
import re
import tempfile
import shutil
import subprocess
import logging
from importlib import import_module

from django.contrib.auth import REDIRECT_FIELD_NAME, authenticate, get_user
from django.http import HttpResponseRedirect
from django.template.response import TemplateResponse
from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.core import mail
from django.core.files.uploadedfile import TemporaryUploadedFile, \
        SimpleUploadedFile
from django.core.urlresolvers import reverse
from django.test.utils import override_settings
from django.test.client import RequestFactory
from django.contrib.auth.models import User, AnonymousUser
from django.template import Context, Template
from django.forms import ValidationError
from django.core.handlers.wsgi import WSGIRequest
from django.forms.fields import CharField, IntegerField

from oioioi.base import utils
from oioioi.base.tests import TestCase
from oioioi.base.permissions import is_superuser, Condition, make_condition, \
    make_request_condition, RequestBasedCondition, enforce_condition
from oioioi.base.utils import RegisteredSubclassesBase, archive
from oioioi.base.utils import strip_num_or_hash, split_extension
from oioioi.base.utils.execute import execute, ExecuteError
from oioioi.base.fields import DottedNameField, EnumRegistry, EnumField
from oioioi.base.menu import menu_registry, OrderedRegistry, \
    side_pane_menus_registry, MenuRegistry
from oioioi.base.management.commands import import_users
from oioioi.contests.utils import is_contest_admin
from oioioi.base.notification import NotificationHandler
from oioioi.base.middleware import UserInfoInErrorMessage
from oioioi.base.main_page import register_main_page_view, \
        unregister_main_page_view


if not getattr(settings, 'TESTS', False):
    print >> sys.stderr, 'The tests are not using the required test ' \
            'settings from test_settings.py.'
    print >> sys.stderr, 'Make sure the tests are run ' \
            'using \'python setup.py test\' or ' \
            '\'DJANGO_SETTINGS_MODULE=oioioi.test_settings python ' \
            'manage.py test\'.'
    sys.exit(1)

basedir = os.path.dirname(__file__)


class TestPermsTemplateTags(TestCase):
    fixtures = ('test_users',)

    def test_check_perms(self):
        admin = User.objects.get(username='test_admin')
        user = User.objects.get(username='test_user')
        template = Template(
                '{% load check_perm %}'
                '{% check_perm "auth.add_user" for "whatever" as p %}'
                '{% if p %}yes{% endif %}')
        self.assertEqual(template.render(Context(dict(user=admin))), 'yes')
        self.assertEqual(template.render(Context(dict(user=user))), '')


class TestIndex(TestCase):
    fixtures = ('test_users', 'test_contest')

    def test_login(self):
        with self.assertNumQueriesLessThan(50):
            response = self.client.get('/', follow=True)
        self.assertNotIn('test_user', response.content)
        self.assert_(self.client.login(username='test_user'))
        with self.assertNumQueriesLessThan(60):
            response = self.client.get('/', follow=True)
        self.assertIn('test_user', response.content)
        login_url = reverse('login')
        with self.assertNumQueriesLessThan(50):
            response = self.client.get(login_url)
        self.assertEqual(302, response.status_code)
        with self.assertNumQueriesLessThan(50):
            response = self.client.get(login_url,
                {REDIRECT_FIELD_NAME: '/test'})
        self.assertEqual(302, response.status_code)
        self.assertTrue(response['Location'].endswith('/test'))

    def test_admin_login_redirect(self):
        response = self.client.get('/c/c/admin/login/?next=/admin/')
        self.assertRedirects(response, '/login/?next=%2Fadmin%2F',
                             target_status_code=302)

    def test_logout(self):
        self.client.get('/', follow=True)
        logout_url = reverse('logout')
        response = self.client.get(logout_url)
        self.assertEqual(405, response.status_code)
        self.assertNotIn('My submissions', response.content)
        self.assertIn('OIOIOI', response.content)
        self.assertIn('method is not allowed', response.content)
        self.client.login(username='test_user')
        response = self.client.post(logout_url)
        self.assertEqual(200, response.status_code)
        self.assertIn('been logged out', response.content)

    def test_index(self):
        with self.assertNumQueriesLessThan(90):
            self.client.login(username='test_user')
            response = self.client.get('/', follow=True)
            self.assertNotIn('navbar-login', response.content)
            self.assertNotIn('System Administration', response.content)
        with self.assertNumQueriesLessThan(75):
            self.client.login(username='test_admin')
            response = self.client.get('/', follow=True)
            self.assertNotIn('navbar-login', response.content)
            self.assertIn('System Administration', response.content)

    def test_accounts_menu(self):
        response = self.client.get('/', follow=True)
        self.assertNotIn('Change password', response.content)
        self.client.login(username='test_user')
        response = self.client.get('/', follow=True)
        self.assertIn('Change password', response.content)


class TestIndexNoContest(TestCase):
    fixtures = ('test_users',)

    def test_no_contest(self):
        with self.assertNumQueriesLessThan(50):
            response = self.client.get('/')
            self.assertIn('There are no contests available to logged out',
                    response.content)
        with self.assertNumQueriesLessThan(50):
            self.client.login(username='test_admin')
            response = self.client.get('/')
            self.assertIn('This is a new OIOIOI installation',
                    response.content)

    def test_navbar_login(self):
        response = self.client.get('/')
        self.assertIn('navbar-login', response.content)


class TestMainPage(TestCase):
    fixtures = ('test_users',)
    custom_templates = settings.TEMPLATES
    custom_templates[0]['DIRS'].append(os.path.join(basedir, 'templates'))

    @override_settings(TEMPLATES=custom_templates)
    def test_custom_main_page(self):
        @register_main_page_view(order=0,
                                 condition=Condition(lambda request: False))
        def inaccessible(request):
            pass

        @register_main_page_view(order=1)
        def accessible(request):
            return TemplateResponse(request, 'index.html')

        try:
            response = self.client.get('/')
            self.assertIn('This is a test index template', response.content)
        finally:
            # Perform cleanup regardless of the test failure/success
            unregister_main_page_view(inaccessible)
            unregister_main_page_view(accessible)


class TestOrderedRegistry(TestCase):
    def test_ordered_registry(self):
        reg = OrderedRegistry()
        reg.register(1, 12)
        reg.register(3)
        reg.register(2, 3)
        reg.register(4)
        self.assertListEqual([2, 1, 3, 4], list(reg))
        reg.unregister(3)
        self.assertListEqual([2, 1, 4], list(reg))
        self.assertEqual(len(reg), 3)


class TestMenu(TestCase):
    fixtures = ['test_users', 'test_contest', 'test_icon']

    def setUp(self):
        self.saved_menu = menu_registry._registry
        menu_registry._registry = []

    def tearDown(self):
        menu_registry._registry = self.saved_menu

    def _render_menu(self, user=None):
        self.client.login(username=user)
        return self.client.get(reverse('index'), follow=True).content

    def test_menu(self):
        menu_registry.register('test2', 'Test Menu Item 2',
                lambda request: '/test_menu_link2', order=2)
        menu_registry.register('test1', 'Test Menu Item 1',
                lambda request: '/test_menu_link1', order=1)
        response = self._render_menu()
        self.assertIn('Test Menu Item 1', response)
        self.assertIn('Test Menu Item 2', response)
        self.assertIn('/test_menu_link1', response)
        self.assertIn('/test_menu_link2', response)
        self.assertLess(response.index('Test Menu Item 1'),
                response.index('Test Menu Item 2'))

    def test_is_contest_admin(self):
        admin = User.objects.get(username='test_admin')
        user = User.objects.get(username='test_user')
        menu_registry.register('test', 'Test Admin Menu',
                lambda request: '/test_admin_link',
                condition=is_contest_admin)
        response = self._render_menu(user=admin)
        self.assertIn('test_admin_link', response)
        response = self._render_menu(user=user)
        self.assertNotIn('test_admin_link', response)

    def test_menu_item_attrs_escape(self):
        menu_registry.register('test', 'Test Menu',
                lambda request: '/test_link',
                attrs={'name<>\'"&': 'value<>\'"&'})
        response = self._render_menu()
        self.assertIn('name&lt;&gt;&#39;&quot;&amp;='
                '"value&lt;&gt;&#39;&quot;&amp;"', response)

    def test_side_menus_registry(self):
        admin = User.objects.get(username='test_admin')
        user = User.objects.get(username='test_user')
        old_keys = side_pane_menus_registry.keys
        old_items = side_pane_menus_registry.items
        side_pane_menus_registry.keys = []
        side_pane_menus_registry.items = []
        try:
            side_pane_menus_registry.register(menu_registry, order=200)
            admin_menu_registry = MenuRegistry("Admin Menu", is_superuser)
            side_pane_menus_registry.register(admin_menu_registry, order=100)

            menu_registry.register('test', 'Test Menu Item',
                lambda request: '/test_menu_link', order=2)
            admin_menu_registry.register('test_admin', 'Test Admin Item',
                lambda request: '/spam', order=100)

            response = self._render_menu(user=user)
            self.assertIn('class="contesticon"', response)
            self.assertNotIn('User Menu', response)
            self.assertNotIn('Admin Menu', response)

            response = self._render_menu(user=admin)
            self.assertNotIn('class="contesticon"', response)
            self.assertIn('User Menu', response)
            self.assertIn('Admin Menu', response)
            self.assertLess(response.index('Test Admin Item'),
                    response.index('Test Menu Item'))
        finally:
            side_pane_menus_registry.keys = old_keys
            side_pane_menus_registry.items = old_items


class TestErrorHandlers(TestCase):
    fixtures = ['test_users']

    def setUp(self):
        """Modify the client so that it follows to handler500 view on error,
           retaining cookies."""
        self._orig_handler = self.client.handler
        self._orig_get = self.client.get
        self._orig_login = self.client.login
        self._orig_logout = self.client.logout
        self._user = AnonymousUser()
        self._req = None

        def wrapped_handler500(request):
            from oioioi.base.views import handler500
            r = WSGIRequest(request)
            r.session = import_module(settings.SESSION_ENGINE).SessionStore()
            if self._user:
                r.user = self._user
            self._req = r
            return handler500(r)

        def custom_get(*args, **kwargs):
            try:
                return self._orig_get(*args, **kwargs)
            except StandardError:
                try:
                    self.client.handler = wrapped_handler500
                    resp = self._orig_get(*args, **kwargs)
                    resp.request = self._req
                    return resp
                finally:
                    self.client.handler = self._orig_handler

        def custom_logout(*args, **kwargs):
            self._orig_logout(*args, **kwargs)
            self._user = AnonymousUser()

        def custom_login(*args, **kwargs):
            self._orig_login(*args, **kwargs)
            self._user = User.objects.get(**kwargs)

        self.client.get = custom_get
        self.client.logout = custom_logout
        self.client.login = custom_login

    def ajax_get(self, url):
        return self.client.get(url, HTTP_X_REQUESTED_WITH='XMLHttpRequest')

    def assertHtml(self, response, code):
        self.assertEqual(response.status_code, code)
        self.assertIn('<html', response.content)
        self.assertIn('text/html', response['Content-type'])

    def assertPlain(self, response, code):
        self.assertEqual(response.status_code, code)
        self.assertNotIn('<html', response.content)
        self.assertLess(len(response.content), 250)
        self.assertIn('text/plain', response['Content-type'])

    def test_ajax_errors(self):
        self.assertPlain(self.ajax_get('/nonexistant'), 404)
        self.assertPlain(self.ajax_get(reverse('force_permission_denied')),
                         403)
        self.assertPlain(self.ajax_get(reverse('force_error')), 500)

    def test_errors(self):
        self.assertHtml(self.client.get('/nonexistant'), 404)
        self.assertHtml(self.client.get(reverse('force_permission_denied')),
                        403)
        self.assertHtml(self.client.get(reverse('force_error')), 500)

    def test_user_in_500(self):
        from oioioi.base.views import ForcedError

        mid = UserInfoInErrorMessage()

        self.client.login(username='test_admin')
        req = self.client.get(reverse('force_error')).request
        mid.process_exception(req, ForcedError())
        self.assertEqual(req.META['USERNAME'], 'test_admin')
        self.assertEqual(req.META['IS_AUTHENTICATED'], 'True')

        self.client.login(username='test_user')
        req = self.client.get(reverse('force_error')).request
        mid.process_exception(req, ForcedError())
        self.assertEqual(req.META['USERNAME'], 'test_user')
        self.assertEqual(req.META['IS_AUTHENTICATED'], 'True')

        self.client.logout()
        req = self.client.get(reverse('force_error')).request
        mid.process_exception(req, ForcedError())
        self.assertEqual(req.META['IS_AUTHENTICATED'], 'False')


class TestUtils(TestCase):
    def test_classinit(self):
        TestUtils.classinit_called_counter = 0
        try:
            class C(utils.ClassInitBase):
                @classmethod
                def __classinit__(cls):
                    TestUtils.classinit_called_counter += 1
            self.assertEqual(TestUtils.classinit_called_counter, 1)

            class _D(C):
                pass
            self.assertEqual(TestUtils.classinit_called_counter, 2)
        finally:
            del TestUtils.classinit_called_counter

    def test_registered_subclasses_meta(self):
        class C(utils.RegisteredSubclassesBase):
            abstract = True
        self.assertEqual(C.subclasses, [])

        class C1(C):
            pass
        self.assertIn(C1, C.subclasses)

        class C2(C1):
            pass
        self.assertIn(C2, C.subclasses)
        self.assertIn(C2, C1.subclasses)

        class D(utils.RegisteredSubclassesBase):
            pass
        self.assertEqual(D.subclasses, [D])
        self.assertEqual(len(C.subclasses), 2)

    def test_object_with_mixins(self):
        class Mixin1(object):
            name = 'mixin1'
            has_mixin1 = True

        class Mixin2(object):
            name = 'mixin2'

        class Mixin3(object):
            name = 'mixin3'

        class Base(utils.ObjectWithMixins):
            mixins = [Mixin1]

        class Derived1(Base):
            mixins = [Mixin2]

        class Derived2(Base):
            mixins = [Mixin2]
            allow_too_late_mixins = True
            name = 'derived2'

        class Derived3(Base):
            def __init__(self, foo):
                self.name = 'derived3'
                self.foo = foo
        Derived3.mix_in(Mixin2)

        class Derived4(Base):
            name = 'derived4'
        self.assertEqual(Base().name, 'mixin1')
        self.assertEqual(Derived1().name, 'mixin2')
        self.assertEqual(Derived2().name, 'mixin2')
        self.assertEqual(Derived3(foo='bar').name, 'derived3')
        self.assertTrue(Derived2().has_mixin1)
        self.assertEqual(Derived4().name, 'derived4')

        Derived2.mix_in(Mixin3)
        with self.assertRaises(AssertionError):
            Derived1.mix_in(Mixin3)

    def test_mixins_mro(self):
        class Base(utils.ObjectWithMixins):
            name = 'base'

            def foo(self):
                return 'bar'

        class Mixin1(object):
            name = 'mixin1'

            def foo(self):
                return 'eggs'
        Base.mix_in(Mixin1)

        class Mixin2(object):
            name = 'mixin2'

            def foo(self):
                return 'spam'
        Base.mix_in(Mixin2)

        self.assertEqual(Base().name, 'mixin1')
        self.assertEqual(Base().foo(), 'eggs')

    def test_registered_with_mixing(self):
        class Base(utils.ObjectWithMixins, utils.RegisteredSubclassesBase):
            spam = 'spam'

        class Derived(Base):
            derived = 'spam'

        class BaseMixin(object):
            basemixin = 'spam'

        class DerivedMixin(object):
            derivedmixin = 'spam'

        Derived.mix_in(DerivedMixin)
        Base.mix_in(BaseMixin)

        self.assertEquals(Derived().derivedmixin, 'spam')
        self.assertEquals(Derived().basemixin, 'spam')
        with self.assertRaises(AttributeError):
            _none = Base().derivedmixin

        self.assertListEqual(Base.subclasses, [Base, Derived])
        self.assertListEqual(Derived.subclasses, [Derived])

    def test_memoized(self):
        memoized_random = utils.memoized(random.random)
        self.assertEqual(memoized_random(), memoized_random())
        memoized_randbits = utils.memoized(random.getrandbits)
        self.assertNotEqual(memoized_randbits(64), memoized_randbits(63))

    def test_reset_memoized(self):
        memoized_random = utils.memoized(random.random)
        r1 = memoized_random()
        utils.reset_memoized(memoized_random)
        r2 = memoized_random()
        self.assertNotEqual(r1, r2)

    def test_utils_dont_need_settings(self):
        subprocess_env = os.environ.copy()
        subprocess_env.pop('DJANGO_SETTINGS_MODULE', None)
        subprocess_code = """
import sys
import oioioi.base.utils
if 'oioioi.default_settings' in sys.modules:
    sys.exit(1)
else:
    sys.exit(0)"""
        ret = subprocess.call([sys.executable, '-c', subprocess_code],
              env=subprocess_env)
        self.assertEqual(ret, 0)


class TestAllWithPrefix(TestCase):
    def test_all_with_prefix(self):
        t = Template('{% load all_with_prefix %}{% all_with_prefix a_ %}')
        context = Context(dict(a_foo='foo', a_bar='bar', b_baz='baz'))
        rendered = t.render(context)
        self.assertIn('foo', rendered)
        self.assertIn('bar', rendered)
        self.assertNotIn('baz', rendered)


class TestDottedFieldClass(RegisteredSubclassesBase):
    modules_with_subclasses = ['tests.test_dotted_field_classes']
    abstract = True


class TestDottedFieldSubclass(TestDottedFieldClass):
    description = 'Description'


class TestFields(TestCase):
    def test_dotted_name_field(self):
        field = DottedNameField('oioioi.base.tests.tests.TestDottedFieldClass')
        field.validate('oioioi.base.tests.tests.TestDottedFieldSubclass', None)
        with self.assertRaises(ValidationError):
            field.validate('something.stupid', None)
        with self.assertRaises(ValidationError):
            field.validate('oioioi.base.tests.tests.TestDottedFieldClass',
                           None)
        self.assertEqual(list(field.get_choices(include_blank=False)),
                [('oioioi.base.tests.tests.TestDottedFieldSubclass',
                    TestDottedFieldSubclass.description)])

    def test_dotted_name_field_module_loading(self):
        if 'oioioi.base.tests.test_dotted_field_classes' in sys.modules:
            # Well, it must have been already loaded by
            # TestDottedFieldClass.load_subclasses...
            return
        TestDottedFieldClass.load_subclasses()
        self.assertIn('oioioi.base.tests.test_dotted_field_classes',
                sys.modules)


class TestEnumField(TestCase):
    def setUp(self):
        self.registry = EnumRegistry()
        self.registry.register('OK', 'OK')
        self.registry.register('OK', 'Should be ignored (duplicate)')
        self.registry.register('ERR', 'Error')

    def test_basic_usage(self):
        field = EnumField(self.registry)
        self.assertEqual(sorted(list(field.choices)),
                [('ERR', 'Error'), ('OK', 'OK')])
        with self.assertRaises(ValidationError):
            field.validate('FOO', None)

    def test_serialization(self):
        """Test if choices aren't serialized by migration."""
        first_field = EnumField(self.registry)
        first_serialized = first_field.deconstruct()

        self.registry.register('MAYBE', "You tell me if it's wrong or not")
        second_field = EnumField(self.registry)
        second_serialized = second_field.deconstruct()

        self.assertEqual(first_serialized, second_serialized)


class TestExecute(TestCase):
    def test_echo(self):
        self.assertEqual("foo\n", execute("echo foo"))

    def test_echo_with_list_command(self):
        self.assertEqual("-n test\n", execute(['echo', '-n test']))

    def test_cat_with_string_input(self):
        input_text = 'hello there!'
        output_text = execute('cat', stdin=input_text)
        self.assertEqual(input_text, output_text)

    def test_error(self):
        with self.assertRaises(ExecuteError):
            execute('exit 12')  # random error code

    def test_ignored_error(self):
        execute('exit 12', ignore_errors=True)

    def test_ignored_error_list(self):
        execute('exit 12', errors_to_ignore=(12, 15, 16))
        execute('exit 15', errors_to_ignore=(12, 15, 16))
        with self.assertRaises(ExecuteError):
            execute('return 14')

    def test_line_splitting(self):
        self.assertListEqual(['foo', 'lol'],
                             execute('echo "foo\nlol"', split_lines=True))

    def test_env(self):
        self.assertEqual('bar\n', execute('echo $foo', env={'foo': 'bar'}))

    def test_cwd(self):
        self.assertEqual(execute(['cat', os.path.basename(__file__)],
                cwd=os.path.dirname(__file__)), open(__file__, 'rb').read())


class TestMisc(TestCase):
    def test_reload_settings_for_coverage(self):
        import oioioi.test_settings
        reload(oioioi.test_settings)
        import oioioi.default_settings
        reload(oioioi.default_settings)

    def test_uploaded_file_name(self):
        tmp_file = TemporaryUploadedFile('whatever',
                'application/octet-stream', 0, 'utf-8')
        with utils.uploaded_file_name(tmp_file) as name:
            self.assertEquals(name, tmp_file.file.name)
        mem_file = SimpleUploadedFile('whatever', 'hello42')
        with utils.uploaded_file_name(mem_file) as name:
            self.assertTrue(name.endswith('whatever'))
            self.assertEqual(open(name, 'rb').read(), 'hello42')
        self.assertFalse(os.path.exists(name))

    def test_make_html_links(self):
        test = [('url1', 'name1'), ('url2', 'name2'), ('url3', 'name3',
                                                       'POST')]
        links = utils.make_html_links(test)
        self.assertEqual(len(links.split(' | ')), 3)
        self.assertIn('url1', links)
        self.assertIn('name1', links)
        self.assertIn('url2', links)
        self.assertIn('name2', links)
        self.assertIn('href="#"', links)
        self.assertIn('data-post-url="url3"', links)
        self.assertIn('name3', links)


class TestRegistration(TestCase):
    def test_registration_form_fields(self):
        response = self.client.get(reverse('registration_register'))
        form = response.context['form']
        self.assertIn('first_name', form.fields)
        self.assertIn('last_name', form.fields)

    def _register_user(self):
        self.client.post(reverse('registration_register'), {
            'username': 'test_foo',
            'first_name': 'Foo',
            'last_name': 'Bar',
            'email': 'foo@bar.com',
            'password1': 'xxx',
            'password2': 'xxx',
        })

    def _assert_user_active(self):
        user = User.objects.get(username='test_foo')
        self.assertTrue(user.is_active)
        self.assertEqual(user.first_name, 'Foo')
        self.assertEqual(user.last_name, 'Bar')

    @override_settings(SEND_USER_ACTIVATION_EMAIL=True)
    def test_registration_with_activation_email(self):
        self._register_user()
        self.assertEqual(len(mail.outbox), 1)
        message = mail.outbox[0]
        del mail.outbox
        self.assertEqual(list(message.to), ['foo@bar.com'])
        url = re.search('^http://[^/]*(/.*)$', message.body, re.M).group(1)
        self.client.get(url)
        self._assert_user_active()

    @override_settings(SEND_USER_ACTIVATION_EMAIL=False)
    def test_registration_without_activation_email(self):
        self._register_user()
        self._assert_user_active()


class TestArchive(TestCase):
    good_files = ['archive.tgz', 'archive.zip']
    bad_files = ['archive-with-symlink.tgz', 'archive-with-hardlink.tgz']
    base_dir = os.path.join(os.path.dirname(__file__), 'files')

    def test_archive(self):
        tmpdir = tempfile.mkdtemp()
        a = os.path.join(tmpdir, 'a')
        b = os.path.join(tmpdir, 'b')
        try:
            for good_file in self.good_files:
                filename = os.path.join(self.base_dir, good_file)
                archive.extract(filename, tmpdir)
                self.assertTrue(os.path.exists(a))
                self.assertTrue(os.path.exists(b))
                self.assertEqual(open(a, 'rb').read().strip(), 'foo')
                self.assertEqual(open(b, 'rb').read().strip(), 'bar')
                os.unlink(a)
                os.unlink(b)
                self.assertEqual(archive.Archive(filename).filenames(), ['a',
                                                                         'b'])
            for bad_file in self.bad_files:
                with self.assertRaises(archive.UnsafeArchive):
                    archive.extract(os.path.join(self.base_dir, bad_file),
                                    tmpdir)
        finally:
            shutil.rmtree(tmpdir)

    def test_size_calc(self):
        for good_file, expected_size in zip(self.good_files, (8, 8)):
            filename = os.path.join(self.base_dir, good_file)
            self.assertEqual(archive.Archive(filename).extracted_size(),
                             expected_size)


class TestAdmin(TestCase):
    fixtures = ['test_users']

    def test_admin_delete(self):
        self.client.login(username='test_admin')
        user = User.objects.get(username='test_user')
        url = reverse('oioioiadmin:auth_user_delete', args=(user.id,))
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertIn('User: test_user', response.content)
        self.assertIn('well', response.content)
        response = self.client.post(url, {'post': 'yes'}, follow=True)
        self.assertIn('was deleted successfully', response.content)
        self.assertEqual(User.objects.filter(username='test_user').count(), 0)

    def test_import_users(self):
        user_count_before = User.objects.count()
        filename = os.path.join(basedir, 'files', 'users.csv')
        manager = import_users.Command()
        manager.run_from_argv(['manage.py', 'import_users', filename])

        self.assertEqual(User.objects.count(), user_count_before + 2)
        user4 = authenticate(username='test_user4', password='spam')
        self.assertEqual(user4.first_name, "Test")
        self.assertEqual(user4.last_name, "User 4")
        self.assertEqual(user4.email, "test_user4@example.com")

        self.assertFalse(User.objects.filter(username='username').exists())


class TestBaseViews(TestCase):
    fixtures = ['test_users']

    def test_edit_profile(self):
        self.client.login(username='test_user')
        user = User.objects.get(username='test_user')
        url = reverse('edit_profile')
        response = self.client.get(url)
        self.assertIn('registration/registration_form.html',
                [t.name for t in response.templates])
        self.assertEqual(response.context['form'].instance, user)

        data = {'username': 'test_user', 'first_name': 'fn',
                'last_name': 'ln', 'email': 'foo@bar.com'}
        response = self.client.post(url, data, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(User.objects.filter(username='test_user').count(), 1)
        user = User.objects.get(username='test_user')
        self.assertEqual(user.first_name, 'fn')
        self.assertEqual(user.last_name, 'ln')
        self.assertEqual(user.email, 'foo@bar.com')

    def test_username_change_attempt(self):
        url = reverse('edit_profile')
        data = {'username': 'changed_user', 'first_name': 'fn',
                'last_name': 'ln', 'email': 'foo@bar.com'}
        response = self.client.post(url, data, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(User.objects.filter(username='changed_user')
                .count(), 0)
        self.assertEqual(User.objects.filter(username='test_user').count(), 1)

    def test_profile_dynamic_fields(self):
        from oioioi.base.preferences import PreferencesFactory, \
                PreferencesSaved

        def callback_func(sender, **kwargs):
            self.assertEquals(sender.cleaned_data['dog'], 'Janusz')
            self.assertEquals(sender.cleaned_data['answer'], 42)

        try:
            PreferencesFactory.add_field(
                'dog',
                CharField,
                lambda n, u: 'Andrzej',
                label='Doggy'
            )
            PreferencesFactory.add_field(
                'answer',
                IntegerField,
                lambda n, u: 72,
                label="The answer to everything"
            )
            PreferencesSaved.connect(callback_func)

            self.client.login(username='test_user')
            url = reverse('edit_profile')

            response = self.client.get(url)

            for text in ['Doggy', 'Andrzej', '72', 'The answer to everything']:
                self.assertIn(text, response.content)

            data = {'username': 'test_user', 'first_name': 'fn',
                    'last_name': 'ln', 'email': 'foo@bar.com',
                    'dog': 'Janusz', 'answer': '42'}
            self.client.post(url, data, follow=True)
            # callback_func should be called already
        finally:
            PreferencesSaved.disconnect(callback_func)
            PreferencesFactory.remove_field('dog')
            PreferencesFactory.remove_field('answer')


class TestBackendMiddleware(TestCase):
    fixtures = ['test_users']

    def test_backend_middleware(self):
        self.client.login(username='test_user')
        response = self.client.get(reverse('index'))
        self.assertEquals('test_user', response.context['user'].username)
        self.assertEquals('oioioi.base.tests.IgnorePasswordAuthBackend',
            response.context['user'].backend)


class TestNotifications(TestCase):
    fixtures = ['test_users']

    def test_notification_registration(self):
        flags = {}
        flags['got_notification'] = False

        def notification_function(arguments):
            message = "Test"
            message_arguments = {}
            user = User.objects.get(username='test_user')
            NotificationHandler.send_notification(user,
                    'test_notification', message, message_arguments)
            flags['got_notification'] = True
        NotificationHandler.register_notification('test_notification',
                notification_function)
        logger = logging.getLogger('oioioi')
        logger.info("Test notification",
            extra={'notification': 'test_notification'})
        self.assertTrue(flags['got_notification'])


class TestCondition(TestCase):
    fixtures = ['test_users']

    def _fake_request_factory(self):
        factory = RequestFactory()

        def get_request():
            request = factory.request()
            request.user = AnonymousUser()
            return request

        return get_request

    def setUp(self):
        self.alwaysTrue = Condition(lambda x: True)
        self.alwaysFalse = Condition(lambda x: False)
        self.returnArg = Condition(lambda x: x)
        self.factory = self._fake_request_factory()

    def test_and_operator(self):
        true_and_true = self.alwaysTrue & self.alwaysTrue
        true_and_false = self.alwaysTrue & self.alwaysFalse
        true_and_arg = self.alwaysTrue & self.returnArg

        self.assertTrue(true_and_true(1))
        self.assertFalse(true_and_false(1))
        self.assertTrue(true_and_arg(True))
        self.assertFalse(true_and_arg(False))

    def test_or_operator(self):
        true_or_true = self.alwaysTrue | self.alwaysTrue
        true_or_false = self.alwaysTrue | self.alwaysFalse
        false_or_arg = self.alwaysFalse | self.returnArg

        self.assertTrue(true_or_true(1))
        self.assertTrue(true_or_false(1))
        self.assertTrue(false_or_arg(True))
        self.assertFalse(false_or_arg(False))

    def test_inverse_operator(self):
        not_true = ~self.alwaysTrue
        not_false = ~self.alwaysFalse
        not_arg = ~self.returnArg

        self.assertFalse(not_true(1))
        self.assertTrue(not_false(1))
        self.assertTrue(not_arg(False))
        self.assertFalse(not_arg(True))

    def test_make_condition(self):
        @make_condition()
        def otherReturnArg(arg):
            return arg

        self.assertTrue(isinstance(otherReturnArg, Condition))
        self.assertTrue(otherReturnArg(True))
        self.assertFalse(otherReturnArg(False))

    def test_request_condition(self):
        @make_request_condition
        def requestReturnArg(request):
            return request

        self.assertTrue(isinstance(requestReturnArg, RequestBasedCondition))
        self.assertTrue(requestReturnArg(True))
        self.assertFalse(requestReturnArg(False))
        # Test not throwing exception with too many arguments
        self.assertTrue(requestReturnArg(True, 1))

    def test_enforce_condition_success(self):
        @enforce_condition(self.alwaysTrue)
        def example_view(request):
            return 314

        self.assertEqual(314, example_view(1))

    def test_enforce_condition_failure_with_template(self):
        # pylint: disable=assignment-from-no-return
        @enforce_condition(self.alwaysFalse, 'base.html')
        def example_view(request):
            pass

        res = example_view(1)
        self.assertTrue(isinstance(res, TemplateResponse))

    def test_enforce_condition_failure_without_template(self):
        # pylint: disable=assignment-from-no-return
        @enforce_condition(self.alwaysFalse)
        def example_view(request):
            pass

        request = self.factory()
        res = example_view(request)
        self.assertTrue(isinstance(res, HttpResponseRedirect))

    def test_enforce_failing_condition_without_require_login(self):
        @enforce_condition(self.alwaysFalse, login_redirect=False)
        def example_view(request):
            pass

        request = self.factory()
        with self.assertRaises(PermissionDenied):
            example_view(request)

    def test_enforce_passing_condition_without_require_login(self):
        @enforce_condition(self.alwaysTrue, login_redirect=False)
        def example_view(request):
            return 314

        request = self.factory()
        self.assertEqual(314, example_view(request))


class TestLoginChange(TestCase):
    fixtures = ['test_users', 'test_contest']

    def setUp(self):
        self.invalid_logins = ['#', 'p@n', ' user', 'user\xc4\x99']
        self.valid_logins = ['test_user', 'user', 'uSeR', 'U__4']
        self.user = User.objects.get(username='test_user')
        self.client.login(username=self.user.username)
        self.client.get('/', follow=True)
        self.url_index = reverse('index')
        self.url_edit_profile = reverse('edit_profile')

    def test_message(self):
        for l in self.invalid_logins:
            self.user.username = l
            self.user.save()

            response = self.client.get(self.url_index, follow=True)
            self.assertIn('contains not allowed characters', response.content)

        for l in self.valid_logins:
            self.user.username = l
            self.user.save()

            response = self.client.get(self.url_index, follow=True)
            self.assertNotIn('contains not allowed characters',
                    response.content)

    def test_can_change_login_from_invalid(self):
        for l in self.invalid_logins:
            self.user.username = l
            self.user.save()

            response = self.client.get(self.url_edit_profile)
            # The html strings underneath may change with any django upgrade.
            self.assertIn('<input class="form-control" id="id_username" '
                    'maxlength="30" name="username" type="text" '
                    'value="%s" />' % l, response.content)

            self.client.post(self.url_edit_profile, {'username': 'valid_user'},
                    follow=True)
            self.assertEqual(self.user.username, l)

            response = self.client.post(self.url_index, follow=True)
            self.assertNotIn('contains not allowed characters',
                    response.content)

            response = self.client.get(self.url_edit_profile)
            self.assertIn('<input class="form-control" id="id_username" '
                    'maxlength="30" name="username" type="text" '
                    'value="valid_user" readonly />', response.content)

    def test_login_cannot_change_from_valid(self):
        for l in self.valid_logins:
            self.user.username = l
            self.user.save()

            response = self.client.get(self.url_edit_profile)
            self.assertIn('<input class="form-control" id="id_username" '
                          'maxlength="30" name="username" type="text" '
                          'value="%s" readonly />' % l, response.content)

            response = self.client.post(self.url_edit_profile,
                    {'username': 'valid_user'}, follow=True)
            self.assertEqual(self.user.username, l)
            self.assertIn('You cannot change your username.', response.content)

            response = self.client.get(self.url_index, follow=True)
            self.assertNotIn('contains not allowed characters',
                    response.content)

            response = self.client.get(self.url_edit_profile)
            self.assertNotIn('valid_user', response.content)

    def test_failed_login_change(self):
        url_edit_profile = reverse('edit_profile')

        self.user.username = self.invalid_logins[0]
        self.user.save()

        for l in self.invalid_logins:
            self.client.post(url_edit_profile, {'username': l},
                    follow=True)
            self.assertEqual(self.user.username, self.invalid_logins[0])


@override_settings(LANGUAGE_CODE='pl')
class TestTranslate(TestCase):
    def test_translate(self):
        get_data = {'query': 'contest'}
        url = reverse('translate')
        response = self.client.get(url, get_data)
        self.assertEqual(200, response.status_code)
        self.assertIn('konkurs', response.content)


class TestFileUtils(TestCase):
    def test_split_ext(self):
        normal = ['a.b.c.d.pdf', '.bashrc', '.a.conf', '/a/b/c/a2.cpp',
                  'a.xml', 'aaaaa...avi', '/a-b.png', '_ab_123.jpg', 'abc.tar',
                  'my_file']
        for name in normal:
            their = os.path.splitext(name)
            ours = split_extension(name)
            self.assertEqual(ours, their)

        weird = ['test.tar.gz', 'test.tar.xz', '/a/b/c/test.tar.bz2']
        for name in weird:
            self.assertNotIn('.', split_extension(name)[0])

    def test_strip_num_or_hash(self):
        cases = {
            'abc_1.pdf': 'abc.pdf',
            'abc_123.pdf': 'abc.pdf',
            'abc_45HKmyT.pdf': 'abc.pdf',
            'abc_1.tar.gz': 'abc.tar.gz',
            'abc_45HKmyT.tar.gz': 'abc.tar.gz',
            'abc.tar_1.gz': 'abc.tar.gz',
            'abc.tar.gz': 'abc.tar.gz',
            '/a/b/abc.tar.gz': '/a/b/abc.tar.gz',
            'my_file': 'my_file',
            'a_1_2.pdf': 'a_1.pdf',
        }

        for (before, after) in cases.iteritems():
            self.assertEqual(strip_num_or_hash(before), after)


class TestUserDeactivationLogout(TestCase):
    fixtures = ['test_users', 'test_contest']

    def setUp(self):
        self.user = User.objects.get(username='test_user')
        self.profile_index = reverse('edit_profile')
        self.client.login(username=self.user.username)
        self.client.get(self.profile_index, follow=True)

    def assert_logged(self, logged=True):
        user = get_user(self.client)
        if logged:
            self.assertTrue(user.is_authenticated())
        else:
            self.assertFalse(user.is_authenticated())

    def test_invalidated_user_logout(self):
        self.assert_logged(True)

        self.user.is_active = False
        self.user.save()

        self.client.get(self.profile_index, follow=True)
        # At this point we should check if user is deactivated and log him out.
        self.assert_logged(False)
