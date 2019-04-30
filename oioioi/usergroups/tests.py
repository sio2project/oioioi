from django.contrib.auth.models import User
from django.urls import reverse
from django.urls.exceptions import NoReverseMatch

from oioioi.base.tests import TestCase
from oioioi.usergroups.models import UserGroup, ActionConfig

class TestAdmin(TestCase):
    fixtures = ['test_users', 'teachers', 'test_action_configs',
                'test_usergroups']

    def test_visibility(self):
        self.assertTrue(self.client.login(username='test_admin'))

        url = reverse('oioioiadmin:auth_user_changelist')
        response = self.client.get(url)
        self.assertContains(response, 'User Groups', count=4)  # sidebar

        url = reverse('oioioiadmin:usergroups_usergroup_changelist')
        response = self.client.get(url)

        self.assertContains(response, 'group 1')
        self.assertContains(response, 'Select user group to change')
        self.assertContains(response, 'id="searchbar"')

        url = reverse('oioioiadmin:usergroups_usergroup_add')
        response = self.client.get(url)

        self.assertContains(response, 'Add user group')
        self.assertNotContains(response, 'Addtion config')
        self.assertContains(response, 'Test User 3 (test_user3)')

        url = reverse('oioioiadmin:usergroups_usergroup_change', args=(1001,))
        response = self.client.get(url)

        self.assertContains(response, 'Change user group')
        self.assertContains(response, 'owners')
        self.assertNotContains(response, 'Action config')
        self.assertContains(response, 'Test User 3 (test_user3)', count=1)
        self.assertContains(response, 'Test Admin (test_admin)', count=2)

        url = reverse('oioioiadmin:usergroups_usergroup_delete', args=(1002,))
        response = self.client.get(url)

        self.assertContains(response, 'Confirm deletion')
        self.assertContains(response, 'User group: empty default group')

        self.assertRaises(NoReverseMatch, reverse, 'oioioiadmin:usergroups_actionconfig_changelist')
        self.assertRaises(NoReverseMatch, reverse,'oioioiadmin:usergroups_actionconfig_add')

    def test_permissions(self):
        self.assertTrue(self.client.login(username='test_admin'))

        url = reverse('oioioiadmin:usergroups_usergroup_changelist')
        self.assertTrue(self.client.get(url).status_code, 200)

        url = reverse('oioioiadmin:usergroups_usergroup_add')
        self.assertTrue(self.client.get(url).status_code, 200)

        url = reverse('oioioiadmin:usergroups_usergroup_change', args=(1001,))
        self.assertTrue(self.client.get(url).status_code, 200)

        url = reverse('oioioiadmin:usergroups_usergroup_delete', args=(1002,))
        self.assertTrue(self.client.get(url).status_code, 200)

        self.assertTrue(self.client.login(username='test_user'))

        url = reverse('oioioiadmin:usergroups_usergroup_changelist')
        self.assertTrue(self.client.get(url).status_code, 403)

        url = reverse('oioioiadmin:usergroups_usergroup_add')
        self.assertTrue(self.client.get(url).status_code, 403)

        url = reverse('oioioiadmin:usergroups_usergroup_change', args=(1001,))
        self.assertTrue(self.client.get(url).status_code, 403)

        url = reverse('oioioiadmin:usergroups_usergroup_delete', args=(1002,))
        self.assertTrue(self.client.get(url).status_code, 403)
        self.assertTrue(self.client.post(url).status_code, 403)

    def test_usergroup_validation(self):
        self.assertTrue(self.client.login(username='test_admin'))
        url = reverse('oioioiadmin:usergroups_usergroup_change', args=(1001,))
        self.client.get(url)

        data = {
            'name': 'group 1',
            'members': (1000, ),
        }
        self.assertContains(self.client.post(url, data), 'This field is required')

        data = {
            'name': 'group 1',
            'owners': (1003,),
            'members': (1000,),
        }
        self.assertContains(self.client.post(url, data), 'is not one of the available choices')

        data = {
            'name': 'group 1',
            'owners': (1000,),
        }
        self.assertEqual(self.client.post(url, data).status_code, 302)


class TestTeachersViews(TestCase):
    fixtures = ['test_users', 'teachers', 'test_action_configs', 'test_usergroups']

    def test_visibility(self):
        self.assertTrue(self.client.login(username='test_user')) # teacher

        url = reverse('teacher_usergroups_list')
        response = self.client.get(url)
        self.assertContains(response, 'User Groups', count=3)  # sidebar
        self.assertContains(response, 'Your Groups')
        self.assertContains(response, 'teacher group')
        self.assertNotContains(response, 'group 1')

        url = reverse('teacher_usergroups_add_group')
        response = self.client.get(url)
        self.assertContains(response, 'New group')

        url = reverse('teacher_usergroup_detail', kwargs={'usergroup_id': 1004})
        response = self.client.get(url)
        self.assertContains(response, 'Group teacher and admin group')
        self.assertContains(response, 'usergroups/join')
        self.assertContains(response, 'Test User 3')
        self.assertContains(response, 'Group modifications')

        url = reverse('teacher_usergroup_detail', kwargs={'usergroup_id': 1005})
        response = self.client.get(url)
        self.assertContains(response, 'Group addition false group')
        self.assertNotContains(response, 'usergroups/join')
        self.assertContains(response, 'Addition to this group is currently disabled')

        url = reverse('delete_usergroup_confirmation', kwargs={'usergroup_id': 1005})
        response = self.client.get(url)
        self.assertContains(response, 'Confirm deletion')
        self.assertContains(response, 'User group: addition false group')

        self.assertTrue(self.client.login(username='test_user3')) # normal user
        url = reverse('usergroups_user_join', kwargs={
            'key': ActionConfig.objects.filter(id=1000).first().key
        })
        response = self.client.get(url)
        self.assertContains(response, 'Confirm joining group group 1')

    def test_permissions(self):
        self.assertTrue(self.client.login(username='test_user3'))  # regular user

        url = reverse('teacher_usergroups_list')
        self.assertEqual(self.client.get(url).status_code, 403)

        url = reverse('teacher_usergroups_add_group')
        self.assertEqual(self.client.get(url).status_code, 403)

        url = reverse('teacher_usergroup_detail', kwargs={'usergroup_id': 1004})
        self.assertEqual(self.client.get(url).status_code, 403)

        url = reverse('delete_usergroup_confirmation', kwargs={'usergroup_id': 1005})
        self.assertEqual(self.client.get(url).status_code, 403)
        self.assertEqual(self.client.post(url).status_code, 403)

        self.assertTrue(self.client.login(username='test_user2'))  # inactive teacher

        url = reverse('teacher_usergroups_list')
        self.assertEqual(self.client.get(url).status_code, 403)

        url = reverse('teacher_usergroups_add_group')
        self.assertEqual(self.client.get(url).status_code, 403)

        url = reverse('teacher_usergroup_detail', kwargs={'usergroup_id': 1004})
        self.assertEqual(self.client.get(url).status_code, 403)

        url = reverse('delete_usergroup_confirmation', kwargs={'usergroup_id': 1005})
        self.assertEqual(self.client.get(url).status_code, 403)
        self.assertEqual(self.client.post(url).status_code, 403)

        self.assertTrue(self.client.login(username='teacher2005')) # active teacher

        url = reverse('teacher_usergroup_detail', kwargs={'usergroup_id': 1004})
        self.assertEqual(self.client.get(url).status_code, 403)

    def test_addition(self):
        self.assertTrue(self.client.login(username='test_user')) # teacher

        url = reverse('teacher_usergroups_add_group')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        data = {
            'name': 'new group'
        }

        self.assertEqual(UserGroup.objects.count(), 5)
        self.assertEqual(ActionConfig.objects.count(), 9)
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(UserGroup.objects.count(), 6)
        self.assertEqual(ActionConfig.objects.count(), 11)
        self.assertTrue(UserGroup.objects.filter(name='new group').exists())

        group = UserGroup.objects.filter(name='new group').first()
        self.assertEqual(group.owners.values().count(), 1)
        self.assertEqual(group.owners.values().first()['username'], 'test_user')
        self.assertEqual(group.members.values().count(), 0)
        self.assertFalse(group.addition_config.enabled)

    def test_deletion(self):
        self.assertTrue(self.client.login(username='test_user'))  # teacher

        url = reverse('delete_usergroup_confirmation', kwargs={'usergroup_id': 1005})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        self.assertEqual(UserGroup.objects.count(), 5)
        self.assertEqual(ActionConfig.objects.count(), 9)
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(UserGroup.objects.count(), 4)
        self.assertEqual(ActionConfig.objects.count(), 7)

        url = reverse('delete_usergroup_confirmation', kwargs={'usergroup_id': 1004})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        self.assertEqual(UserGroup.objects.count(), 4)
        self.assertEqual(ActionConfig.objects.count(), 7)
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(UserGroup.objects.count(), 3)
        self.assertEqual(ActionConfig.objects.count(), 6)

    def test_delete_members(self):
        self.assertTrue(self.client.login(username='test_user'))  # teacher

        url = reverse('teacher_usergroup_detail', kwargs={'usergroup_id': 1004})
        self.assertEqual(self.client.get(url).status_code, 200)
        data = {
            'member': [1002, 1003]
        }

        url = reverse('usergroups_delete_members', kwargs={'usergroup_id': 1004})
        self.assertEqual(UserGroup.objects.filter(id=1004).first().members.count(), 2)
        self.assertTrue(self.client.post(url, data), 302)
        self.assertEqual(UserGroup.objects.filter(id=1004).first().members.count(), 0)

    def test_joining_group(self):
        self.assertTrue(self.client.login(username='test_user3'))  # regular user

        key = UserGroup.objects.filter(id=1002).first().addition_config.key
        url = reverse('usergroups_user_join', kwargs={'key': key})

        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(UserGroup.objects.filter(id=1002).first().members.count(), 0)

        key = UserGroup.objects.filter(id=1001).first().addition_config.key
        url = reverse('usergroups_user_join', kwargs={'key': key})

        user = User.objects.filter(username='test_user3').first()
        data = {
            'confirmation': True,
            'confirmation_sent': True
        }

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(UserGroup.objects.filter(id=1001).first().members.count(), 2)
        self.assertFalse(UserGroup.objects.filter(id=1001).filter(members__in=[user]).exists())

        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(UserGroup.objects.filter(id=1001).first().members.count(), 3)
        self.assertTrue(UserGroup.objects.filter(id=1001).filter(members__in=[user]).exists())

        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(UserGroup.objects.filter(id=1001).first().members.count(), 3)


class TestSharing(TestCase):
    fixtures = ['test_users', 'teachers', 'test_action_configs', 'test_usergroups']

    def test_visibility(self):
        self.assertTrue(self.client.login(username='test_user'))  # teacher

        url = reverse('teacher_usergroup_detail', kwargs={'usergroup_id': 1003})
        response = self.client.get(url)
        self.assertContains(response, 'Owners')
        self.assertContains(response, 'usergroups/share')

    def test_deleting_owners(self):
        self.assertTrue(self.client.login(username='test_user'))  # teacher

        self.assertEqual(UserGroup.objects.filter(id=1005).first().owners.values().count(), 2)
        url = reverse('usergroups_delete_owners', kwargs={'usergroup_id': 1005})
        data = {
            'owner': (1001, 1002)
        }

        response = self.client.post(url, data, follow=True)
        self.assertContains(response, 'You cannot renounce ownership')
        self.assertEqual(UserGroup.objects.filter(id=1005).first().owners.values().count(), 2)

        data['owner'] = (1002,)
        self.assertEqual(self.client.post(url, data).status_code, 302)
        self.assertEqual(UserGroup.objects.filter(id=1005).first().owners.values().count(), 1)

    def test_becoming_owner(self):
        self.assertTrue(self.client.login(username='test_user'))  # teacher

        key = UserGroup.objects.filter(id=1003).first().sharing_config.key
        url = reverse('usergroups_become_owner', kwargs={'key': key})
        self.assertEqual(self.client.get(url).status_code, 302)
        self.assertEqual(UserGroup.objects.filter(id=1003).first().owners.values().count(), 1)

        self.assertTrue(self.client.login(username='teacher2005'))  # teacher

        self.assertEqual(self.client.get(url).status_code, 302)
        self.assertEqual(UserGroup.objects.filter(id=1003).first().owners.values().count(), 2)

        key = UserGroup.objects.filter(id=1005).first().sharing_config.key
        url = reverse('usergroups_become_owner', kwargs={'key': key})
        self.assertEqual(self.client.get(url).status_code, 302)
        self.assertEqual(UserGroup.objects.filter(id=1005).first().owners.values().count(), 2)

        self.assertTrue(self.client.login(username='test_user3'))  # regular user

        key = UserGroup.objects.filter(id=1003).first().sharing_config.key
        url = reverse('usergroups_become_owner', kwargs={'key': key})
        self.assertEqual(self.client.get(url).status_code, 403)

