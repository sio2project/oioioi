import json
from django.test import TestCase
from django.core.urlresolvers import reverse
from oioioi.base.tests import check_not_accessible
from oioioi.contests.models import Contest, ProblemInstance
from oioioi.questions.models import Message


class TestQuestions(TestCase):
    fixtures = ['test_users', 'test_contest', 'test_full_package',
            'test_messages']

    def test_visibility(self):
        contest = Contest.objects.get()
        all_messages = ['problem-question', 'contest-question',
                'public-answer', 'private-answer']
        url = reverse('contest_messages', kwargs={'contest_id': contest.id})

        def check_visibility(*should_be_visible):
            response = self.client.get(url)
            for m in all_messages:
                if m in should_be_visible:
                    self.assertIn(m, response.content)
                else:
                    self.assertNotIn(m, response.content)
        self.client.login(username='test_user')
        check_visibility('public-answer', 'private-answer')
        self.client.login(username='test_user2')
        check_visibility('public-answer')
        self.client.login(username='test_admin')
        check_visibility('public-answer', 'private-answer')

    def test_new_labels(self):
        self.client.login(username='test_user')
        contest = Contest.objects.get()
        list_url = reverse('contest_messages',
                kwargs={'contest_id': contest.id})
        response = self.client.get(list_url)
        self.assertEqual(response.content.count('>NEW<'), 2)
        public_answer = Message.objects.get(topic='public-answer')
        response = self.client.get(reverse('message', kwargs={
            'contest_id': contest.id, 'message_id': public_answer.id}))
        self.assertIn('public-answer-body', response.content)
        self.assertNotIn('contest-question', response.content)
        self.assertNotIn('problem-question', response.content)
        response = self.client.get(list_url)
        self.assertEqual(response.content.count('>NEW<'), 1)

    def test_ask_and_reply(self):
        self.client.login(username='test_user2')
        contest = Contest.objects.get()
        pi = ProblemInstance.objects.get()
        url = reverse('add_contest_message', kwargs={'contest_id': contest.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertIn('form', response.context)
        form = response.context['form']
        self.assertEqual(len(form.fields['category'].choices) - 1, 2)

        post_data = {
                'category': 'p_%d' % (pi.id,),
                'topic': 'the-new-question',
                'content': 'the-new-body',
            }
        response = self.client.post(url, post_data)
        self.assertEqual(response.status_code, 302)
        new_question = Message.objects.get(topic='the-new-question')
        self.assertEqual(new_question.content, 'the-new-body')
        self.assertEqual(new_question.kind, 'QUESTION')
        self.assertIsNone(new_question.top_reference)
        self.assertEqual(new_question.contest, contest)
        self.assertEqual(new_question.problem_instance, pi)
        self.assertEqual(new_question.author.username, 'test_user2')

        self.client.login(username='test_admin')
        list_url = reverse('contest_messages',
                kwargs={'contest_id': contest.id})
        response = self.client.get(list_url)
        self.assertIn('the-new-question', response.content)

        url = reverse('message_reply', kwargs={'contest_id': contest.id,
            'message_id': new_question.id})
        response = self.client.get(url)
        self.assertIn('form', response.context)

        post_data = {
                'kind': 'PUBLIC',
                'topic': 're-new-question',
                'content': 're-new-body',
            }
        response = self.client.post(url, post_data)
        self.assertEqual(response.status_code, 302)
        new_reply = Message.objects.get(topic='re-new-question')
        self.assertEqual(new_reply.content, 're-new-body')
        self.assertEqual(new_reply.kind, 'PUBLIC')
        self.assertEqual(new_reply.top_reference, new_question)
        self.assertEqual(new_reply.contest, contest)
        self.assertEqual(new_reply.problem_instance, pi)
        self.assertEqual(new_reply.author.username, 'test_admin')

        self.client.login(username='test_user')
        q_url = reverse('message', kwargs={'contest_id': contest.id,
            'message_id': new_question.id})
        check_not_accessible(self, q_url)
        repl_url = reverse('message', kwargs={'contest_id': contest.id,
            'message_id': new_reply.id})
        response = self.client.get(repl_url)
        self.assertEqual(response.status_code, 200)
        self.assertIn('re-new-question', response.content)
        self.assertIn('re-new-body', response.content)
        self.assertNotIn('the-new-question', response.content)
        self.assertNotIn('the-new-body', response.content)
        response = self.client.get(list_url)
        self.assertIn(repl_url, response.content)
        self.assertIn('re-new-question', response.content)
        self.assertNotIn('the-new-question', response.content)

        self.client.login(username='test_user2')
        response = self.client.get(q_url)
        self.assertEqual(response.status_code, 200)
        self.assertIn('the-new-question', response.content)
        self.assertIn('the-new-body', response.content)
        self.assertIn('re-new-body', response.content)
        response = self.client.get(list_url)
        self.assertIn(q_url, response.content)
        self.assertIn('re-new-question', response.content)
        self.assertNotIn('the-new-question', response.content)

    def test_filtering(self):
        self.client.login(username='test_admin')
        contest = Contest.objects.get()
        url = reverse('contest_messages', kwargs={'contest_id': contest.id})

        get_data = {'author': 'test_admin'}
        response = self.client.get(url, get_data)
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('general-question', response.content)
        self.assertNotIn('problem-question', response.content)
        self.assertIn('public-answer', response.content)
        self.assertIn('private-answer', response.content)

        get_data['author'] = 'test_user'
        response = self.client.get(url, get_data)
        self.assertEqual(response.status_code, 200)
        self.assertIn('general-question', response.content)
        self.assertIn('problem-question', response.content)
        self.assertNotIn('public-answer', response.content)
        self.assertNotIn('private-answer', response.content)

        get_data['category'] = 'r_1'
        response = self.client.get(url, get_data)
        self.assertEqual(response.status_code, 200)
        self.assertIn('general-question', response.content)
        self.assertNotIn('problem-question', response.content)
        self.assertNotIn('public-answer', response.content)
        self.assertNotIn('private-answer', response.content)

        get_data['category'] = 'p_1'
        response = self.client.get(url, get_data)
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('general-question', response.content)
        self.assertIn('problem-question', response.content)
        self.assertNotIn('public-answer', response.content)
        self.assertNotIn('private-answer', response.content)

        self.client.login(username='test_user')
        response = self.client.get(url, get_data)
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('general-question', response.content)
        self.assertNotIn('problem-question', response.content)
        self.assertNotIn('public-answer', response.content)
        self.assertIn('private-answer', response.content)

    def test_authors_list(self):
        self.client.login(username='test_admin')
        contest = Contest.objects.get()
        url = reverse('get_messages_authors',
                      kwargs={'contest_id': contest.id})
        response = self.client.get(url, {'substr': ''})
        self.assertEquals(404, response.status_code)
        response = self.client.get(url)
        self.assertEquals(404, response.status_code)

        response = self.client.get(url, {'substr': 't'})
        response = json.loads(response.content)
        self.assertListEqual(['test_admin (Test Admin)',
                              'test_user (Test User)'], response)

        response = self.client.get(url, {'substr': 'test admin'})
        response = json.loads(response.content)
        self.assertListEqual(['test_admin (Test Admin)'], response)

        self.client.login(username='test_user')
        check_not_accessible(self, url)

    def test_change_category(self):
        pi = ProblemInstance.objects.get()
        r = pi.round
        q = Message.objects.get(topic="problem-question")
        a1, a2 = Message.objects.filter(top_reference=q)

        def change_category(msg, cat):
            url = reverse('oioioiadmin:questions_message_change',
                          args=(msg.id,))
            self.client.login(username='test_admin')
            response = self.client.get(url)
            self.assertIn('form', response.context)

            post_data = {
                'kind': msg.kind,
                'category': cat,
                'topic': msg.topic,
                'content': msg.content,
            }
            response = self.client.post(url, post_data)
            self.assertEqual(response.status_code, 302)

        # Change a1 to round question
        change_category(a1, 'r_%d' % r.id)
        q = Message.objects.get(topic="problem-question")
        a1, a2 = Message.objects.filter(top_reference=q)
        self.assertEqual(a1.round, r)
        self.assertEqual(a2.round, r)
        self.assertEqual(q.round, r)
        self.assertTrue(a1.problem_instance is None)
        self.assertTrue(a2.problem_instance is None)
        self.assertTrue(q.problem_instance is None)
        # Change q to problem question
        change_category(q, 'p_%d' % pi.id)
        q = Message.objects.get(topic="problem-question")
        a1, a2 = Message.objects.filter(top_reference=q)
        self.assertEqual(a1.problem_instance, pi)
        self.assertEqual(a2.problem_instance, pi)
        self.assertEqual(q.problem_instance, pi)
        self.assertEqual(a1.round, pi.round)
        self.assertEqual(a2.round, pi.round)
        self.assertEqual(q.round, pi.round)

    def test_change_denied(self):
        self.client.login(username='test_user')
        msg = Message.objects.filter(author__username='test_admin')[0]
        url = reverse('oioioiadmin:questions_message_change',
                      args=(msg.id,))
        check_not_accessible(self, url)
