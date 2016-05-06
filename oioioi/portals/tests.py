from django.test.utils import override_settings
from django.contrib.auth.models import AnonymousUser
from django.core.urlresolvers import reverse
from django.utils.translation import ugettext_lazy as _

from oioioi.base.tests import TestCase
from oioioi.contests.current_contest import ContestMode
from oioioi.portals.models import Portal, Node
from oioioi.portals.actions import portal_url
from oioioi.portals.widgets import render_panel, \
        register_widget
from oioioi.problems.models import Problem, ProblemSite


def get_portal():
    return Portal.objects.get(owner__username='test_user')


@override_settings(CONTEST_MODE=ContestMode.neutral)
class TestPortalUtils(TestCase):
    fixtures = ['test_users', 'test_portals']

    def test_portal_url(self):
        portal = get_portal()
        root = portal.root
        child1 = root.children.get(short_name='child1')

        url = '/~test_user/'
        self.assertEqual(portal_url(portal=portal), url)
        self.assertEqual(portal_url(portal=portal, path=''), url)
        self.assertEqual(portal_url(node=root), url)

        url = '/~test_user/child1'
        self.assertEqual(portal_url(portal=portal, path='child1'), url)
        self.assertEqual(portal_url(node=child1), url)
        self.assertEqual(portal_url(node=child1, action='show_node'), url)
        self.assertEqual(portal_url(node=child1, action='edit_node'),
                         url + '?action=edit_node')

        url = '/~test_user/?action=manage_portal'
        self.assertEqual(portal_url(portal=portal, action='manage_portal'),
                         url)

        portal = Portal.objects.get(owner=None)
        url = '/portal/'
        self.assertEqual(portal_url(portal=portal), url)
        self.assertEqual(portal_url(portal=portal, path=''), url)
        self.assertEqual(portal_url(node=portal.root), url)


class TestPortalModels(TestCase):
    fixtures = ['test_users', 'test_portals']

    def test_get_siblings(self):
        node = get_portal().root
        self.assertQuerysetEqual(node.get_siblings(), [])
        self.assertQuerysetEqual(node.get_siblings(include_self=True),
                                 ['<Node: Root>'])

        node = node.children.get(short_name='child1')
        self.assertQuerysetEqual(node.get_siblings(),
                                 ['<Node: Child 2>'])
        self.assertQuerysetEqual(node.get_siblings(include_self=True),
                                 ['<Node: Child 1>', '<Node: Child 2>'])

    def test_get_ancestors_including_self(self):
        node = get_portal().root
        self.assertQuerysetEqual(node.get_ancestors_including_self(),
                                 ['<Node: Root>'])

        node = node.children.get(short_name='child1')
        self.assertQuerysetEqual(node.get_ancestors_including_self(),
                                 ['<Node: Root>', '<Node: Child 1>'])

    def test_get_siblings_including_self(self):
        node = get_portal().root
        self.assertQuerysetEqual(node.get_siblings_including_self(),
                                 ['<Node: Root>'])

        node = node.children.get(short_name='child1')
        self.assertQuerysetEqual(node.get_siblings_including_self(),
                                 ['<Node: Child 1>', '<Node: Child 2>'])

    def test_get_path(self):
        root = get_portal().root
        self.assertEqual(root.get_path(), '')

        child1 = root.children.get(short_name='child1')
        self.assertEqual(child1.get_path(), 'child1')

        child1.short_name = 'child123'
        child1.save()
        self.assertEqual(child1.get_path(), 'child123')

        child2 = root.children.get(short_name='child2')
        self.assertEqual(child2.get_path(), 'child2')

        grandchild1 = child1.children.get()
        self.assertEqual(grandchild1.get_path(), 'child123/grandchild1')

        grandchild1.parent = child2
        grandchild1.save()
        self.assertEqual(grandchild1.get_path(), 'child2/grandchild1')

        child2.short_name = 'child234'
        child2.save()
        self.assertEqual(grandchild1.get_path(), 'child234/grandchild1')

        child2.parent = child1
        child2.save()
        self.assertEqual(grandchild1.get_path(),
                         'child123/child234/grandchild1')


@override_settings(CONTEST_MODE=ContestMode.neutral)
class TestPortalViews(TestCase):
    fixtures = ['test_users', 'test_portals']

    def _test_create_portal_view(self, create_url, portal_root_url, username):
        create_url = reverse(create_url)

        response = self.client.get(create_url)
        self.assertEqual(response.status_code, 403)

        self.client.login(username=username)
        response = self.client.get(create_url)
        self.assertRedirects(response, portal_root_url)

        self.client.post(portal_root_url + '?action=delete_portal',
                         data={'confirmation': ''})

        response = self.client.get(create_url)
        self.assertEqual(response.status_code, 200)

        response = self.client.post(create_url, data={'confirmation': ''})
        self.assertRedirects(response, portal_root_url)

        response = self.client.get(portal_root_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, _("Main page"))

    def test_create_user_portal_view(self):
        self._test_create_portal_view('create_user_portal', '/~test_user/',
                                      'test_user')

    def test_create_global_portal_view(self):
        self._test_create_portal_view('create_global_portal', '/portal/',
                                      'test_admin')

    def test_admin_buttons(self):
        show = _("Show node")
        edit = _("Edit node")
        add = _("Add child node")
        delete = _("Delete node")
        manage = _("Manage portal")
        all = {show, edit, add, delete, manage}
        root = {show, edit, add, manage}

        def assertAdminButtons(username, path, buttons):
            if username is not None:
                self.client.login(username=username)
            else:
                self.client.logout()

            response = self.client.get(portal_url(portal=get_portal(),
                                                  path=path))
            for button in buttons:
                self.assertContains(response, button)
            for button in all - buttons:
                self.assertNotContains(response, button)

        assertAdminButtons(None, '', set())
        assertAdminButtons('test_user', '', root)
        assertAdminButtons('test_user2', '', set())
        assertAdminButtons('test_user', 'child1', all)
        assertAdminButtons('test_admin', 'child1', all)

    def test_show_node_view(self):
        response = self.client.get(portal_url(portal=get_portal()))
        self.assertContains(response, 'a05e')

        response = self.client.get(portal_url(portal=get_portal(),
                                              path='child1'))
        self.assertContains(response, 'b864')

    def test_admin_access(self):
        def assertAdminAccess(url):
            self.client.logout()
            response = self.client.get(url)
            self.assertEquals(response.status_code, 403)

            self.client.login(username='test_user')
            response = self.client.get(url)
            self.assertEquals(response.status_code, 200)

            self.client.login(username='test_user2')
            response = self.client.get(url)
            self.assertEquals(response.status_code, 403)

            self.client.login(username='test_admin')
            response = self.client.get(url)
            self.assertEquals(response.status_code, 200)

        for action in ('edit_node', 'add_node', 'delete_node'):
            assertAdminAccess(portal_url(portal=get_portal(),
                                         path='child1', action=action))

        for action in ('manage_portal', 'portal_tree_json', 'delete_portal'):
            assertAdminAccess(portal_url(portal=get_portal(),
                                         action=action))

    def test_edit_node_view(self):
        self.client.login(username='test_user')

        node = get_portal().root.children.get(short_name='child2')
        response = self.client.post(portal_url(node=node,
                                               action='edit_node'),
                                    data={'full_name': '81dc',
                                          'short_name': 'child1',
                                          'panel_code': 'e10a'})
        self.assertEqual(response.status_code, 200)
        root = get_portal().root
        self.assertQuerysetEqual(root.get_children(),
                                 ['<Node: Child 1>', '<Node: Child 2>'])

        response = self.client.post(portal_url(portal=get_portal(),
                                               action='edit_node'),
                                    data={'full_name': 'b40d',
                                          'panel_code': 'e23f'})
        self.assertRedirects(response, portal_url(portal=get_portal()))
        node = get_portal().root
        self.assertEqual(node.full_name, 'b40d')
        self.assertEqual(node.panel_code, 'e23f')

    def test_add_node_view(self):
        self.client.login(username='test_user')

        root = get_portal().root
        response = self.client.post(portal_url(node=root,
                                               action='add_node'),
                                    data={'full_name': '3e4a',
                                          'short_name': 'child1',
                                          'panel_code': '5ac3'})
        self.assertEqual(response.status_code, 200)
        self.assertQuerysetEqual(root.get_children(),
                                 ['<Node: Child 1>', '<Node: Child 2>'])

        response = self.client.post(portal_url(portal=get_portal(),
                                               path='child2',
                                               action='add_node'),
                                    data={'short_name': 'grandchild2',
                                          'full_name': 'Grandchild 2',
                                          'panel_code': '18e0'})
        self.assertRedirects(response, portal_url(portal=get_portal(),
                                                  path='child2/grandchild2'))
        node = get_portal().root.children.get(short_name='child2')
        self.assertEqual(node.children.count(), 1)
        node = node.children.get()
        self.assertEqual(node.short_name, 'grandchild2')
        self.assertEqual(node.full_name, 'Grandchild 2')
        self.assertEqual(node.panel_code, '18e0')

    def test_delete_node_view(self):
        self.client.login(username='test_user')

        response = self.client.post(portal_url(portal=get_portal(),
                                              path='child1',
                                              action='delete_node'))
        self.assertRedirects(response, portal_url(portal=get_portal(),
                                                  path='child1'))

        response = self.client.post(portal_url(portal=get_portal(),
                                               path='child1',
                                               action='delete_node'),
                                    data={'confirmation': ''})
        self.assertRedirects(response, portal_url(portal=get_portal()))

        node = get_portal().root
        self.assertQuerysetEqual(node.get_children(), ['<Node: Child 2>'])

    def test_portal_tree_json_view(self):
        self.client.login(username='test_user')
        response = self.client.get(portal_url(portal=get_portal(),
                                              action='portal_tree_json'))
        self.assertJSONEqual(response.content, '''
                [
                    {
                        "id": 1,
                        "short_name": "",
                        "label": "Root",
                        "children": [
                            {
                                "id": 2,
                                "short_name": "child1",
                                "label": "Child 1",
                                "children": [
                                    {
                                        "id": 4,
                                        "short_name": "grandchild1",
                                        "label": "Grandchild 1",
                                        "children": []
                                    }
                                ]
                            },
                            {
                                "id": 3,
                                "short_name": "child2",
                                "label": "Child 2",
                                "children": []
                            }
                        ]
                    }
                ]
            ''')

    def test_move_node_view(self):
        def assertMoveStatus(username, node, target, position, status_code):
            if username is not None:
                self.client.login(username=username)
            else:
                self.client.logout()

            response = self.client.get(reverse('move_node'),
                                       data={'node': node, 'target': target,
                                             'position': position})
            self.assertEqual(response.status_code, status_code)

        assertMoveStatus('test_user', 2, 3, 'blahblah', 400)
        assertMoveStatus('test_user', 2, 999, 'inside', 400)
        assertMoveStatus(None, 2, 3, 'inside', 400)
        assertMoveStatus('test_user2', 2, 3, 'inside', 400)
        assertMoveStatus('test_user', 2, 1, 'before', 400)
        assertMoveStatus('test_user', 999, 3, 'inside', 400)
        assertMoveStatus('test_user', 2, 5, 'inside', 400)
        assertMoveStatus('test_admin', 2, 5, 'inside', 400)
        assertMoveStatus('test_user', 1, 2, 'inside', 400)
        assertMoveStatus('test_user', 1, 2, 'after', 400)

        assertMoveStatus('test_user', 2, 3, 'inside', 200)
        node = get_portal().root
        self.assertQuerysetEqual(node.get_children(), ['<Node: Child 2>'])
        node = node.children.get()
        self.assertQuerysetEqual(node.get_children(), ['<Node: Child 1>'])
        node = node.children.get()
        self.assertQuerysetEqual(node.get_children(), ['<Node: Grandchild 1>'])

    def test_delete_portal_view(self):
        self.client.login(username='test_user')

        response = self.client.post(portal_url(portal=get_portal(),
                                               action='delete_portal'))
        self.assertRedirects(response, portal_url(portal=get_portal(),
                                                  action='manage_portal'))

        response = self.client.post(portal_url(portal=get_portal(),
                                               action='delete_portal'),
                                    data={'confirmation': ''})
        self.assertRedirects(response, '/', target_status_code=302)

        with self.assertRaises(Portal.DoesNotExist):
            Portal.objects.get(owner__username='test_user')

        with self.assertRaises(Node.DoesNotExist):
            Node.objects.get(pk=1)

    def test_global_portal_view(self):
        response = self.client.get('/portal/')
        self.assertContains(response, 'e071')


class TestMarkdown(TestCase):

    def setUp(self):
        class MockRequest(object):
            def __init__(self):
                self.user = AnonymousUser()

        # mocking up a request below becouse I am NOT testing whole view
        self.request = MockRequest()

        for i in range(1, 5):
            name = 'problem_%s_name' % i
            url_key = 'problem_%s_key' % i
            problem = Problem(name=name, short_name=name, is_public=True)
            problem.save()
            site = ProblemSite(problem=problem, url_key=url_key)
            site.save()

    def test_double_asterisk(self):
        self.assertEquals(render_panel(self.request, '**word**').strip(),
                          '<p><strong>word</strong></p>')
        self.assertEquals(render_panel(self.request, '**word').strip(),
                          '<p>**word</p>')

    def test_youtube_widget(self):
        url = 'https://www.youtube.com/watch?v=pB0CTz5QlOw'
        embed_url = 'https://www.youtube.com/embed/pB0CTz5QlOw'
        rendered = render_panel(self.request, '[[YouTube|%s]]' % url)
        self.assertIn('<iframe src="%s"' % embed_url, rendered)

    def test_problemtable_widget(self):
        urls = [
            'http://127.0.0.1:8000/problemset/problem/problem_1_key/site/',
            'http://wwww.zabawa.pl/problemset/problem/problem_2_key/site/',
            'www.zabawa.pl/problemset/problem/i_dont_exist_key/site/',
            'www.zabawa.pl/problemset/problem/problem_3_key/site/',
            'https://www.zabawa.pl/problemset/problem/problem_3_key/site/',
            'zabawa.pl/problemset/problem/problem_3_name/site/',
            'zabawa.pl/problemset/problem/problem_4_key/site/?key=statement',
        ]
        tag = '[[ProblemTable|%s]]' % ';'.join(urls)

        rendered = render_panel(self.request, tag)
        self.assertEquals(rendered.count('<tr>'), 6)
        self.assertEquals(rendered.count('href'), 5)
        self.assertNotIn('i_dont_exist', rendered)
        self.assertIn('>problem_1_name</a>', rendered)
        self.assertIn('>problem_2_name</a>', rendered)
        self.assertIn('>problem_3_name</a>', rendered)
        self.assertIn('>problem_4_name</a>', rendered)
        self.assertIn('problem_1_key/site', rendered)
        self.assertIn('problem_2_key/site', rendered)
        self.assertIn('problem_3_key/site', rendered)
        self.assertIn('problem_4_key/site', rendered)

    def test_duplicate_tag(self):

        class Widget(object):
            def __init__(self, name):
                self.name = name

        with self.assertRaises(ValueError):
            register_widget(Widget('youtube'))
        with self.assertRaises(ValueError):
            register_widget(Widget('problem_table'))
