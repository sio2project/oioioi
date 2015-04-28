from django.test import TestCase
from django.core.urlresolvers import reverse
from django.contrib.auth.models import User
from django.utils.translation import ugettext_lazy as _
from oioioi.portals.models import Portal, Node
from oioioi.portals.utils import portal_url


def get_portal():
    return Portal.objects.get(owner__username='test_user')


class TestModels(TestCase):
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

        grandchild = Node.objects.create(parent=child1, full_name='',
                                         short_name='grandchild',
                                         panel_code='')
        self.assertEqual(grandchild.get_path(), 'child123/grandchild')

        grandchild.parent = child2
        grandchild.save()
        self.assertEqual(grandchild.get_path(), 'child2/grandchild')

        child2.short_name = 'child234'
        child2.save()
        self.assertEqual(grandchild.get_path(), 'child234/grandchild')

        child2.parent = child1
        child2.save()
        self.assertEqual(grandchild.get_path(), 'child123/child234/grandchild')


class TestPortalViews(TestCase):
    fixtures = ['test_users', 'test_portals']

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

            response = self.client.get(portal_url('test_user', path))
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
        response = self.client.get(portal_url('test_user'))
        self.assertContains(response, 'a05e')

        response = self.client.get(portal_url('test_user', 'child1'))
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

        for action in ('edit', 'add', 'delete'):
            assertAdminAccess(portal_url('test_user', 'child1', action))

        for action in ('manage_portal', 'portal_tree_json',
                          'delete_portal'):
            assertAdminAccess(portal_url('test_user', action=action))

    def test_edit_node_view(self):
        self.client.login(username='test_user')
        response = self.client.post(portal_url('test_user', '', 'edit'),
                                    data={'full_name': 'b40d',
                                          'panel_code': 'e23f'})
        self.assertRedirects(response, portal_url('test_user', '', 'edit'))
        node = User.objects.get(username='test_user').portal.root
        self.assertEqual(node.full_name, 'b40d')
        self.assertEqual(node.panel_code, 'e23f')

    def test_add_node_view(self):
        self.client.login(username='test_user')
        response = self.client.post(portal_url('test_user', 'child1', 'add'),
                                    data={'short_name': 'grandchild1',
                                          'full_name': 'bead',
                                          'panel_code': 'acb8'})
        self.assertRedirects(response, portal_url('test_user',
                                                  'child1/grandchild1',
                                                  'edit'))
        node = User.objects.get(username='test_user') \
                .portal.root.children.get(short_name='child1')
        self.assertEqual(node.children.count(), 1)
        node = node.children.get()
        self.assertEqual(node.short_name, 'grandchild1')
        self.assertEqual(node.full_name, 'bead')
        self.assertEqual(node.panel_code, 'acb8')

    def test_delete_node_view(self):
        self.client.login(username='test_user')

        response = self.client.post(portal_url('test_user', 'child1',
                                               'delete'))
        self.assertRedirects(response, portal_url('test_user', 'child1'))

        response = self.client.post(portal_url('test_user', 'child1',
                                               'delete'),
                                    data={'confirmation': ''})
        self.assertRedirects(response, portal_url('test_user', ''))

        node = User.objects.get(username='test_user').portal.root
        self.assertEqual(node.children.count(), 1)
        self.assertEqual(node.children.get().short_name, 'child2')

    def test_portal_tree_json_view(self):
        self.client.login(username='test_user')
        response = self.client.get(portal_url('test_user',
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
                                "children": []
                            },
                            {
                                "id": 4,
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

        assertMoveStatus('test_user', 2, 4, 'blahblah', 404)
        assertMoveStatus('test_user', 2, 999, 'inside', 404)
        assertMoveStatus(None, 2, 3, 'inside', 403)
        assertMoveStatus('test_user2', 2, 4, 'inside', 403)
        assertMoveStatus('test_user', 2, 1, 'before', 404)
        assertMoveStatus('test_user', 999, 4, 'inside', 404)
        assertMoveStatus('test_user', 2, 3, 'inside', 403)
        assertMoveStatus('test_admin', 2, 3, 'inside', 403)
        assertMoveStatus('test_user', 1, 2, 'inside', 404)
        assertMoveStatus('test_user', 1, 2, 'after', 404)

        assertMoveStatus('test_user', 2, 4, 'inside', 200)
        node = User.objects.get(username='test_user').portal.root
        self.assertEqual(node.children.count(), 1)
        node = node.children.get()
        self.assertEqual(node.short_name, 'child2')
        self.assertEqual(node.children.count(), 1)
        node = node.children.get()
        self.assertEqual(node.children.count(), 0)
        self.assertEqual(node.short_name, 'child1')

    def test_delete_portal_view(self):
        self.client.login(username='test_user')

        response = self.client.post(portal_url('test_user',
                                               action='delete_portal'))
        self.assertRedirects(response, portal_url('test_user',
                                                  action='manage_portal'))

        response = self.client.post(portal_url('test_user',
                                               action='delete_portal'),
                                    data={'confirmation': ''})
        self.assertRedirects(response, '/')

        with self.assertRaises(Portal.DoesNotExist):
            Portal.objects.get(owner__username='test_user')

        with self.assertRaises(Node.DoesNotExist):
            Node.objects.get(pk=1)
