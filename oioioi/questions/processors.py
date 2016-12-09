from django.core.urlresolvers import reverse
from django.utils.translation import ungettext
from django.utils.functional import lazy
from oioioi.base.utils import make_navbar_badge
from oioioi.contests.utils import can_enter_contest, is_contest_admin
from oioioi.questions.utils import unanswered_questions
from oioioi.questions.views import new_messages, visible_messages
from oioioi.status.registry import status_registry


def navbar_tip_processor(request):
    if not getattr(request, 'contest', None):
        return {}
    if not request.user.is_authenticated():
        return {}
    if not can_enter_contest(request):
        return {}

    def generator():
        return make_navbar_badge(**navbar_messages_generator(request))
    return {'extra_navbar_right_messages': lazy(generator, unicode)()}


@status_registry.register
def get_messages(request, response):
    response['messages'] = navbar_messages_generator(request)
    return response


def navbar_messages_generator(request):
    if request.contest is None:
        return {}

    is_admin = is_contest_admin(request)
    messages = visible_messages(request)
    visible_ids = messages.values_list('id', flat=True)
    if is_admin:
        messages = unanswered_questions(messages)
    else:
        messages = new_messages(request, messages)
    count = messages.count()
    if count:
        text = ungettext('%(count)d NEW MESSAGE', '%(count)d NEW MESSAGES',
                         count) % {'count': count}

        if count == 1:
            m = messages.get()
            link = reverse('message', kwargs={
                'contest_id': request.contest.id,
                'message_id': m.top_reference_id
                if m.top_reference_id in visible_ids else m.id
            })
        else:
            link = reverse('contest_messages', kwargs={'contest_id':
                                                           request.contest.id})
        return {'link': link, 'text': text, 'id': 'contest_new_messages'}
    else:
        return {'link': None, 'text': None, 'id': 'contest_new_messages'}
