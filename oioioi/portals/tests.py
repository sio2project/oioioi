from django.contrib.auth.models import AnonymousUser
from django.test.utils import override_settings
from django.urls import reverse
from oioioi.base.tests import TestCase
from oioioi.contests.current_contest import ContestMode
from oioioi.portals.actions import portal_url
from oioioi.portals.models import Node, Portal
from oioioi.portals.widgets import register_widget, render_panel
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
        self.assertEqual(
            portal_url(node=child1, action='edit_node'), url + '?action=edit_node'
        )

        url = '/~test_user/?action=manage_portal'
        self.assertEqual(portal_url(portal=portal, action='manage_portal'), url)

        portal = Portal.objects.get(link_name='default')
        url = '/p/default/'
        self.assertEqual(portal_url(portal=portal), url)
        self.assertEqual(portal_url(portal=portal, path=''), url)
        self.assertEqual(portal_url(node=portal.root), url)


class TestPortalModels(TestCase):
    fixtures = ['test_users', 'test_portals']

    def test_get_siblings(self):
        node = get_portal().root
        self.assertQuerySetEqual(node.get_siblings(), [], transform=repr)
        self.assertQuerySetEqual(node.get_siblings(include_self=True), ['<Node: Root>'], transform=repr)

        node = node.children.get(short_name='child1')
        self.assertQuerySetEqual(node.get_siblings(), ['<Node: Child 2>'], transform=repr)
        self.assertQuerySetEqual(
            node.get_siblings(include_self=True), ['<Node: Child 1>', '<Node: Child 2>'], transform=repr
        )

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

        child2.refresh_from_db()
        child2.short_name = 'child234'
        child2.save()
        self.assertEqual(grandchild1.get_path(), 'child234/grandchild1')

        child1.refresh_from_db()
        child2.parent = child1
        child2.save()
        grandchild1.refresh_from_db()
        self.assertEqual(grandchild1.get_path(), 'child123/child234/grandchild1')


@override_settings(CONTEST_MODE=ContestMode.neutral)
class TestPortalViews(TestCase):
    fixtures = [
        'test_users',
        'test_portals',
        'test_contest',
        'test_full_package',
        'test_problem_instance',
        'test_problem_site',
    ]

    def test_create_user_portal_view(self):
        create_url = reverse('create_user_portal')

        response = self.client.get(create_url)
        self.assertEqual(response.status_code, 403)

        self.assertTrue(self.client.login(username='test_user'))
        response = self.client.get(create_url)
        self.assertRedirects(response, '/~test_user/')

        self.client.post(
            '/~test_user/' + '?action=delete_portal', data={'confirmation': ''}
        )

        response = self.client.get(create_url)
        self.assertEqual(response.status_code, 200)

        response = self.client.post(create_url, data=None)
        self.assertRedirects(response, '/portals_main_page/')

        response = self.client.post(create_url, data={'confirmation': ''})
        self.assertRedirects(response, '/~test_user/')

        response = self.client.get('/~test_user/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Main page")

    def test_create_global_portal_view(self):
        create_url = reverse('create_global_portal')

        response = self.client.get(create_url)
        self.assertEqual(response.status_code, 403)

        self.assertTrue(self.client.login(username='test_admin'))

        response = self.client.get(create_url)
        self.assertEqual(response.status_code, 200)

        response = self.client.post(create_url, data=None)
        self.assertRedirects(response, '/portals_main_page/global/')

        response = self.client.post(
            create_url, data={'confirmation': '', 'link_name': 'default'}
        )
        self.assertContains(response, "Portal with this Link name already exists.")

        response = self.client.post(
            create_url, data={'confirmation': '', 'link_name': 'with space'}
        )
        self.assertContains(
            response,
            "Enter a valid 'slug' "
            "consisting of lowercase letters, "
            "numbers, underscores or hyphens.",
            html=True,
        )

        response = self.client.post(
            create_url, data={'confirmation': '', 'link_name': 'glob1'}
        )
        self.assertRedirects(response, '/p/glob1/')

        response = self.client.get('/p/glob1/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Main page")

    def test_admin_buttons(self):
        show = "View page"
        edit = "Edit page"
        add = "Add a subpage"
        delete = "Delete page"
        manage = "Manage portal"
        all = {show, edit, add, delete, manage}
        root = {show, edit, add, manage}

        def assertAdminButtons(username, path, buttons):
            if username is not None:
                self.assertTrue(self.client.login(username=username))
            else:
                self.client.logout()

            response = self.client.get(portal_url(portal=get_portal(), path=path))
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

        response = self.client.get(portal_url(portal=get_portal(), path='child1'))
        self.assertContains(response, 'b864')

    def test_admin_access(self):
        def assertAdminAccess(url):
            self.client.logout()
            response = self.client.get(url)
            self.assertEqual(response.status_code, 403)

            self.assertTrue(self.client.login(username='test_user'))
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)

            self.assertTrue(self.client.login(username='test_user2'))
            response = self.client.get(url)
            self.assertEqual(response.status_code, 403)

            self.assertTrue(self.client.login(username='test_admin'))
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)

        for action in ('edit_node', 'add_node', 'delete_node'):
            assertAdminAccess(
                portal_url(portal=get_portal(), path='child1', action=action)
            )

        for action in ('manage_portal', 'portal_tree_json', 'delete_portal'):
            assertAdminAccess(portal_url(portal=get_portal(), action=action))

    def test_edit_node_view(self):
        self.assertTrue(self.client.login(username='test_user'))

        node = get_portal().root.children.get(short_name='child2')
        response = self.client.post(
            portal_url(node=node, action='edit_node'),
            data={
                'short_name': 'child1',
                'language_versions-0-id': '',
                'language_versions-0-full_name': '81dc',
                'language_versions-0-panel_code': 'e10a',
                'language_versions-0-language': 'en',
                'language_versions-MAX_NUM_FORMS': 1,
                'language_versions-TOTAL_FORMS': 1,
                'language_versions-MIN_NUM_FORMS': 1,
                'language_versions-INITIAL_FORMS': 0,
            },
        )
        self.assertEqual(response.status_code, 200)
        root = get_portal().root
        self.assertQuerySetEqual(
            root.get_children(), ['<Node: Child 1>', '<Node: Child 2>'], transform=repr
        )

        response = self.client.post(
            portal_url(portal=get_portal(), action='edit_node'),
            data={
                'language_versions-0-id': '1',
                'language_versions-0-full_name': 'b40d',
                'language_versions-0-panel_code': 'e23f',
                'language_versions-0-language': 'en',
                'language_versions-0-node': '1',
                'language_versions-MAX_NUM_FORMS': 1,
                'language_versions-TOTAL_FORMS': 1,
                'language_versions-MIN_NUM_FORMS': 1,
                'language_versions-INITIAL_FORMS': 1,
            },
        )
        self.assertRedirects(response, portal_url(portal=get_portal()))
        node = get_portal().root
        self.assertEqual(node.language_versions.get(language='en').full_name, 'b40d')
        self.assertEqual(node.language_versions.get(language='en').panel_code, 'e23f')

    def test_add_node_view(self):
        self.assertTrue(self.client.login(username='test_user'))

        root = get_portal().root
        response = self.client.post(
            portal_url(node=root, action='add_node'),
            data={
                'short_name': 'child1',
                'language_versions-0-id': '',
                'language_versions-0-full_name': '3e4a',
                'language_versions-0-panel_code': '5ac3',
                'language_versions-0-language': 'en',
                'language_versions-MAX_NUM_FORMS': 1,
                'language_versions-TOTAL_FORMS': 1,
                'language_versions-MIN_NUM_FORMS': 1,
                'language_versions-INITIAL_FORMS': 0,
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertQuerySetEqual(
            root.get_children(), ['<Node: Child 1>', '<Node: Child 2>'], transform=repr
        )

        response = self.client.post(
            portal_url(portal=get_portal(), path='child2', action='add_node'),
            data={
                'short_name': 'grandchild2',
                'language_versions-0-id': '',
                'language_versions-0-full_name': 'Grandchild 2',
                'language_versions-0-panel_code': '18e0',
                'language_versions-0-language': 'en',
                'language_versions-MAX_NUM_FORMS': 1,
                'language_versions-TOTAL_FORMS': 1,
                'language_versions-MIN_NUM_FORMS': 1,
                'language_versions-INITIAL_FORMS': 0,
            },
        )
        self.assertRedirects(
            response, portal_url(portal=get_portal(), path='child2/grandchild2')
        )
        node = get_portal().root.children.get(short_name='child2')
        self.assertEqual(node.children.count(), 1)
        node = node.children.get()
        self.assertEqual(node.short_name, 'grandchild2')
        self.assertEqual(
            node.language_versions.get(language='en').full_name, 'Grandchild 2'
        )
        self.assertEqual(node.language_versions.get(language='en').panel_code, '18e0')

    def test_delete_node_view(self):
        self.assertTrue(self.client.login(username='test_user'))

        response = self.client.post(
            portal_url(portal=get_portal(), path='child1', action='delete_node')
        )
        self.assertRedirects(response, portal_url(portal=get_portal(), path='child1'))

        response = self.client.post(
            portal_url(portal=get_portal(), path='child1', action='delete_node'),
            data={'confirmation': ''},
        )
        self.assertRedirects(response, portal_url(portal=get_portal()))

        node = get_portal().root
        self.assertQuerySetEqual(node.get_children(), ['<Node: Child 2>'], transform=repr)

    def test_portal_tree_json_view(self):
        self.assertTrue(self.client.login(username='test_user'))
        response = self.client.get(
            portal_url(portal=get_portal(), action='portal_tree_json')
        )
        self.assertJSONEqual(
            response.content.decode('utf-8'),
            '''
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
            ''',
        )

    def test_move_node_view(self):
        def assertMoveStatus(username, node, target, position, status_code):
            if username is not None:
                self.assertTrue(self.client.login(username=username))
            else:
                self.client.logout()

            response = self.client.get(
                reverse('move_node'),
                data={'node': node, 'target': target, 'position': position},
            )
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
        self.assertQuerySetEqual(node.get_children(), ['<Node: Child 2>'], transform=repr)
        node = node.children.get()
        self.assertQuerySetEqual(node.get_children(), ['<Node: Child 1>'], transform=repr)
        node = node.children.get()
        self.assertQuerySetEqual(node.get_children(), ['<Node: Grandchild 1>'], transform=repr)

    def test_delete_portal_view(self):
        self.assertTrue(self.client.login(username='test_user'))

        response = self.client.post(
            portal_url(portal=get_portal(), action='delete_portal')
        )
        self.assertRedirects(
            response, portal_url(portal=get_portal(), action='manage_portal')
        )

        response = self.client.post(
            portal_url(portal=get_portal(), action='delete_portal'),
            data={'confirmation': ''},
        )
        self.assertRedirects(response, '/portals_main_page/', target_status_code=200)

        with self.assertRaises(Portal.DoesNotExist):
            Portal.objects.get(owner__username='test_user')

        with self.assertRaises(Node.DoesNotExist):
            Node.objects.get(pk=1)

    def test_global_portal_view(self):
        response = self.client.get('/p/second/')
        self.assertContains(response, '701a')

    def test_old_global_portal_view(self):
        response = self.client.get('/portal/')
        self.assertRedirects(response, '/p/default/')

    def test_problem_table_parsing(self):
        self.assertTrue(self.client.login(username='test_user'))
        problem_site_tab_url = (
            reverse('problem_site', kwargs={'site_key': '123'})
            + "?key=related_portal_pages"
        )
        response = self.client.get(problem_site_tab_url)
        self.assertContains(response, 'No related portal pages')

        root = get_portal().root
        response = self.client.post(
            portal_url(node=root, action='add_node'),
            data={
                'short_name': 'new_child',
                'language_versions-0-id': '',
                'language_versions-0-full_name': 'TESTNAME',
                'language_versions-0-panel_code': '[[ProblemTable|{}]]'.format(
                    problem_site_tab_url
                ),
                'language_versions-0-language': 'en',
                'language_versions-MAX_NUM_FORMS': 1,
                'language_versions-TOTAL_FORMS': 1,
                'language_versions-MIN_NUM_FORMS': 1,
                'language_versions-INITIAL_FORMS': 0,
            },
        )
        self.assertRedirects(
            response, portal_url(portal=get_portal(), path='new_child')
        )

        self.assertTrue(root.portal.is_public)
        response = self.client.get(problem_site_tab_url)
        self.assertNotContains(response, 'No related portal pages')
        self.assertContains(response, 'TESTNAME')
        self.assertContains(response, portal_url(portal=get_portal(), path='new_child'))
        self.assertContains(response, 'test_user')

        node = root.children.get(short_name='new_child')
        nlv = node.language_versions.get(language='en')
        response = self.client.post(
            portal_url(node=node, action='edit_node'),
            data={
                'short_name': 'new_child',
                'language_versions-0-id': str(nlv.id),
                'language_versions-0-full_name': 'TESTNAME',
                'language_versions-0-panel_code': 'abcd',
                'language_versions-0-language': 'en',
                'language_versions-MAX_NUM_FORMS': 1,
                'language_versions-TOTAL_FORMS': 1,
                'language_versions-MIN_NUM_FORMS': 1,
                'language_versions-INITIAL_FORMS': 1,
            },
        )
        response = self.client.get(problem_site_tab_url)
        self.assertNotContains(response, 'TESTNAME')


class TestMarkdown(TestCase):
    def setUp(self):
        class MockRequest(object):
            def __init__(self):
                self.user = AnonymousUser()

        # mocking up a request below because I am NOT testing the whole view
        self.request = MockRequest()

        for i in range(1, 5):
            name = 'problem_%s_name' % i
            url_key = 'problem_%s_key' % i
            problem = Problem(
                legacy_name=name, short_name=name, visibility=Problem.VISIBILITY_PUBLIC
            )
            problem.save()
            site = ProblemSite(problem=problem, url_key=url_key)
            site.save()

    def test_double_asterisk(self):
        self.assertEqual(
            render_panel(self.request, '**word**').strip(),
            '<p><strong>word</strong></p>',
        )
        self.assertEqual(render_panel(self.request, '**word').strip(), '<p>**word</p>')

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
        self.assertEqual(rendered.count('<tr>'), 6)
        self.assertEqual(rendered.count('href'), 5)
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

    def test_block_spoiler(self):
        rendered_markdown = render_panel(
            self.request, '>![spoiler text]\n>!spoiler body\n'
        )

        self.assertIn("<details>", rendered_markdown)
        self.assertIn('<summary class="btn btn-link">spoiler text</summary>', rendered_markdown)
        self.assertIn("<p>spoiler body</p>", rendered_markdown)
        self.assertIn("</details>", rendered_markdown)

    def test_block_spoiler_complex_body(self):
        rendered_markdown = render_panel(
            self.request,
            '>![spoiler text]\n>!# header\n>!**bold**\n',
        )

        self.assertIn("<h1>header</h1>", rendered_markdown)
        self.assertIn("<strong>bold</strong>", rendered_markdown)

    def test_block_spoiler_nested(self):
        rendered_markdown = render_panel(
            self.request, '>![first]\n>!>![nested]\n>!>!nested text\n>!first text\n'
        )
        self.assertIn('<summary class="btn btn-link">first</summary>', rendered_markdown)
        self.assertIn('<summary class="btn btn-link">nested</summary>', rendered_markdown)

    def test_block_spoiler_in_sequence(self):
        rendered_markdown = render_panel(
            self.request, '>![first]\n>!first text\n\n>![second]\n>!second text\n'
        )
        self.assertIn('<summary class="btn btn-link">first</summary>', rendered_markdown)
        self.assertIn('<summary class="btn btn-link">second</summary>', rendered_markdown)

    def test_table_element(self):
        rendered_markdown = render_panel(self.request, '|a|b|\n|-|-|\n|1|2|\n')
        self.assertIn("<table", rendered_markdown)
        self.assertIn("<thead>", rendered_markdown)
        self.assertIn("<tbody>", rendered_markdown)
        self.assertIn("<th>a</th>", rendered_markdown)
        self.assertIn("<td>1</td>", rendered_markdown)


class TestMainPageAndPublicPortals(TestCase):
    fixtures = ['test_users', 'test_portals']

    def test_main_page_user(self):
        self.assertTrue(self.client.login(username='test_user'))

        response = self.client.get('/portals_main_page/')
        self.assertEqual(response.status_code, 200)

        self.assertContains(response, '~test_user')
        self.assertNotContains(response, 'p/second')
        self.assertContains(response, 'Default global portal')
        self.assertNotContains(response, 'Portal number 2')

    def test_public_main_page_admin(self):
        self.assertTrue(self.client.login(username='test_admin'))

        response = self.client.get('/portals_main_page/public/')
        self.assertEqual(response.status_code, 200)

        self.assertContains(response, 'Root')
        self.assertNotContains(response, 'p/second')
        self.assertContains(response, 'p/default')
        self.assertNotContains(response, 'seconds root')

    def test_all_main_page_admin(self):
        self.assertTrue(self.client.login(username='test_admin'))

        response = self.client.get('/portals_main_page/all/')
        self.assertEqual(response.status_code, 200)

        self.assertContains(response, 'Portal number 1')
        self.assertContains(response, '~test_user2')
        self.assertContains(response, 'p/default')
        self.assertContains(response, 'seconds root')

    def test_global_main_page_admin(self):
        self.assertTrue(self.client.login(username='test_admin'))

        response = self.client.get('/portals_main_page/global/')
        self.assertEqual(response.status_code, 200)

        self.assertNotContains(response, 'Portal number 1')
        self.assertNotContains(response, 'Portal number 2')
        self.assertContains(response, 'p/default')
        self.assertContains(response, 'p/second')

    def test_main_page_search(self):
        self.assertTrue(self.client.login(username='test_admin'))

        response = self.client.get('/portals_main_page/public/?q=root')
        self.assertEqual(response.status_code, 200)

        self.assertContains(response, 'Portal number 1')
        self.assertNotContains(response, 'Portal number 2')
        self.assertContains(response, 'p/default')

        response = self.client.get('/portals_main_page/all/?q=seCOnd')
        self.assertEqual(response.status_code, 200)

        self.assertNotContains(response, '~test_user')
        self.assertNotContains(response, '~test_user2')
        self.assertNotContains(response, 'p/default')
        self.assertContains(response, 'seconds root')

        response = self.client.get('/portals_main_page/global/?q=global')
        self.assertEqual(response.status_code, 200)

        self.assertNotContains(response, 'Portal number 2')
        self.assertNotContains(response, 'Default global portal')
        self.assertNotContains(response, 'Second global portal')

    def test_user_short_description(self):
        self.assertTrue(self.client.login(username='test_user'))
        response = self.client.post(
            '/~test_user/' + '?action=manage_portal',
            data={'short_description': 'new description'},
        )
        self.assertAlmostEqual(response.status_code, 200)

        response = self.client.get('/portals_main_page/')
        self.assertContains(response, 'new description')

    def test_admin_short_description_and_public(self):
        self.assertTrue(self.client.login(username='test_admin'))
        response = self.client.post(
            '/p/second/' + '?action=manage_portal',
            data={'short_description': 'this will be public', 'is_public': True},
        )

        self.assertAlmostEqual(response.status_code, 200)
        response = self.client.get('/portals_main_page/public/')

        self.assertContains(response, 'p/second')
        self.assertContains(response, 'this will be public')
